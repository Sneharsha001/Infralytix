"""
Infralytix — Workflow Optimizer Service.

Runs a Pareto-optimal multi-cloud instance sweep for a validated workflow DAG.

Architecture
------------
The optimizer follows the same asyncio.gather + graceful-degradation pattern
used by CostComparisonService, extended to evaluate ALL candidate instances
(not just one matched type per provider) and apply Pareto-filtering.

Pipeline
--------
1. Determine the workflow's PEAK resource requirements across all tasks:
       peak_vcpu = max(task.baseline_vcpu for task in workflow.tasks)
       peak_ram  = max(task.baseline_ram_gb for task in workflow.tasks)

   This ensures no task is undersized on the chosen instance.

2. Fetch candidate instance lists from all three providers concurrently via
   asyncio.gather(return_exceptions=True).  Provider failures are isolated:
   a failing provider contributes an error entry to provider_errors and its
   candidates are omitted — the other providers complete normally.

3. Shortlist candidates per provider: keep at most TOP_N_PER_PROVIDER instances
   meeting or exceeding (peak_vcpu, peak_ram), sorted by ascending price.
   Shortlisting keeps the number of evaluate_workflow calls tractable without
   hardcoding instance types.

4. Run evaluate_workflow(workflow, instance_spec) for every shortlisted candidate.
   GPU detection: if the instance type name contains a known GPU hint keyword
   (e.g. 'p3.', 'g4dn', 'NC', 'ND', 'NV') the InstanceSpec.has_gpu is set True.
   Candidates where evaluate_workflow raises WorkflowEvaluationError (fully
   incompatible) are recorded with provider_error and excluded from Pareto analysis.

5. Compute Pareto front: a point (cost_a, time_a) is dominated by (cost_b, time_b)
   iff cost_b <= cost_a AND time_b <= time_a AND (cost_b < cost_a OR time_b < time_a).
   Discard all dominated points.

6. Label the Pareto front:
   - "Fastest"      → minimum makespan_seconds
   - "Cheapest"     → minimum total_cost_usd
   - "Best balance" → minimum normalised Euclidean distance to the ideal point
                      [min_cost, min_time] after min-max scaling both axes across
                      the Pareto front.  When cost == time range == 0, all points
                      tie and "Best balance" is assigned to the first point.

Assumptions (flagged)
---------------------
- TOP_N_PER_PROVIDER = 20: At most 20 eligible instances per provider are evaluated.
  This keeps runtime under 1 second for typical workflows while still covering
  the meaningful portion of the size-price curve.

- Peak resource demand: conservative — every instance in the sweep must have at
  least peak_vcpu vCPUs and peak_ram_gb GB RAM, so that every task in the workflow
  has its minimum required resources available.

- has_gpu detection: heuristic based on instance type name substrings.  A proper
  v2 implementation should query the provider's GPU attribute field directly.

- GCP fetch_price_list returns (list, bool): the bool (is_static) is used only for
  logging; it does not affect Pareto analysis.
"""

from __future__ import annotations

import asyncio
import math
import re
from typing import Final

import httpx

from app.logging.logging import get_logger
from app.schemas.workflow import WorkflowResponse
from app.schemas.workflow_evaluation import InstanceSpec, WorkflowEvaluation
from app.schemas.workflow_optimizer import (
    CandidateResult,
    ParetoPoint,
    WorkflowOptimizeResult,
)
from app.services.pricing.aws_pricing_service import (
    AWSEC2InstancePrice,
    aws_pricing_service,
)
from app.services.pricing.azure_pricing_service import (
    AzureVMInstancePrice,
    azure_pricing_service,
)
from app.services.pricing.gcp_pricing_service import (
    GCPInstancePrice,
    gcp_pricing_service,
)
from app.services.pricing.region_mapping import (
    resolve_aws_region,
    resolve_azure_region,
    resolve_gcp_region,
)
from app.services.workflow_evaluator import WorkflowEvaluationError, evaluate_workflow

logger = get_logger(__name__)

# ─── Configuration ─────────────────────────────────────────────────────────────

#: Maximum number of eligible instances to evaluate per provider.
#: Covers the practical price/size range without evaluating hundreds of variants.
TOP_N_PER_PROVIDER: Final[int] = 20

#: Instance type regex patterns that indicate GPU presence.
_GPU_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # AWS GPU / accelerator families (e.g. p3.2xlarge, g4dn.xlarge, trn1.2xlarge)
    re.compile(r"^(?:p[2-5]|g[2-6][a-z0-9]*|trn\d+|inf\d+)\.", re.IGNORECASE),
    # Azure GPU series (e.g. Standard_NC6, Standard_ND96asr_v4, Standard_NV12)
    re.compile(r"(?:^|_)n[cdv]", re.IGNORECASE),
    # GCP GPU families (e.g. a2-highgpu-1g, a3-highgpu-8g, g2-standard-4) or explicit gpu
    re.compile(r"^(?:a[23]|g2)-|gpu", re.IGNORECASE),
)


def _has_gpu(instance_type: str) -> bool:
    """
    Heuristically detect whether an instance type has GPU capacity.

    Checks the instance type name against known GPU family regex patterns.
    This is a best-effort approach; a production implementation should read the
    provider's explicit GPU attribute from the pricing API response.
    """
    return any(pattern.search(instance_type) is not None for pattern in _GPU_PATTERNS)


# ─── Candidate shortlisting helpers ──────────────────────────────────────────


def _shortlist_aws(
    instances: list[AWSEC2InstancePrice],
    peak_vcpu: int,
    peak_ram_gb: float,
    top_n: int = TOP_N_PER_PROVIDER,
) -> list[AWSEC2InstancePrice]:
    """
    Filter AWS instances to those meeting peak requirements, sorted by price ascending.
    Returns at most *top_n* instances.
    """
    eligible = [
        inst for inst in instances if inst.vcpus >= peak_vcpu and inst.memory_gb >= peak_ram_gb
    ]
    eligible.sort(key=lambda i: i.price_per_hour_usd)
    return eligible[:top_n]


def _shortlist_azure(
    instances: list[AzureVMInstancePrice],
    peak_vcpu: int,
    peak_ram_gb: float,
    top_n: int = TOP_N_PER_PROVIDER,
) -> list[AzureVMInstancePrice]:
    """
    Filter Azure instances to those meeting peak requirements, sorted by price ascending.
    Returns at most *top_n* instances.
    """
    eligible = [
        inst for inst in instances if inst.vcpus >= peak_vcpu and inst.memory_gb >= peak_ram_gb
    ]
    eligible.sort(key=lambda i: i.price_per_hour_usd)
    return eligible[:top_n]


def _shortlist_gcp(
    instances: list[GCPInstancePrice],
    peak_vcpu: int,
    peak_ram_gb: float,
    top_n: int = TOP_N_PER_PROVIDER,
) -> list[GCPInstancePrice]:
    """
    Filter GCP instances to those meeting peak requirements, sorted by price ascending.
    Returns at most *top_n* instances.
    """
    eligible = [
        inst for inst in instances if inst.vcpus >= peak_vcpu and inst.memory_gb >= peak_ram_gb
    ]
    eligible.sort(key=lambda i: i.price_per_hour_usd)
    return eligible[:top_n]


# ─── Pareto logic ─────────────────────────────────────────────────────────────


def compute_pareto_front(
    candidates: list[CandidateResult],
) -> list[CandidateResult]:
    """
    Compute the Pareto-optimal subset of candidates on the (cost, time) plane.

    A candidate *a* is dominated by candidate *b* if:
        b.total_cost_usd <= a.total_cost_usd
        AND b.makespan_seconds <= a.makespan_seconds
        AND (b.total_cost_usd < a.total_cost_usd OR b.makespan_seconds < a.makespan_seconds)

    Dominated candidates are discarded.  The returned list preserves the original
    order of the non-dominated candidates.

    Time complexity: O(n²) — acceptable for n ≤ 60 (3 providers × 20 candidates).
    """
    pareto: list[CandidateResult] = []
    for candidate in candidates:
        cost_a = candidate.evaluation.total_cost_usd
        time_a = candidate.evaluation.makespan_seconds
        dominated = False
        for other in candidates:
            cost_b = other.evaluation.total_cost_usd
            time_b = other.evaluation.makespan_seconds
            if other is candidate:
                continue
            if cost_b <= cost_a and time_b <= time_a and (cost_b < cost_a or time_b < time_a):
                dominated = True
                break
        if not dominated:
            pareto.append(candidate)
    return pareto


def label_pareto_front(pareto: list[CandidateResult]) -> list[ParetoPoint]:
    """
    Assign human-readable labels to the Pareto-optimal candidates.

    Labels assigned:
        "Fastest"      → candidate with minimum makespan_seconds
        "Cheapest"     → candidate with minimum total_cost_usd
        "Best balance" → candidate with minimum normalised Euclidean distance
                         to the ideal point (min_cost, min_time), after
                         min-max normalisation of both axes over the Pareto set.

    When the Pareto front has exactly one point it receives all three labels
    (formatted as "Fastest / Cheapest / Best balance").
    When min == max on one axis (zero range), that axis contributes 0 to the
    normalised distance for all candidates — effectively collapsing the
    multi-objective problem to a single-objective one on the remaining axis.
    """
    if not pareto:
        return []

    costs = [c.evaluation.total_cost_usd for c in pareto]
    times = [c.evaluation.makespan_seconds for c in pareto]

    min_cost, max_cost = min(costs), max(costs)
    min_time, max_time = min(times), max(times)

    cost_range = max_cost - min_cost
    time_range = max_time - min_time

    # ── Compute normalised distances to ideal point (0, 0) ────────────────────
    norm_distances: list[float] = []
    for c in pareto:
        nc = (c.evaluation.total_cost_usd - min_cost) / cost_range if cost_range > 0 else 0.0
        nt = (c.evaluation.makespan_seconds - min_time) / time_range if time_range > 0 else 0.0
        norm_distances.append(math.sqrt(nc**2 + nt**2))

    # ── Identify label winners ─────────────────────────────────────────────────
    fastest_idx = times.index(min_time)
    cheapest_idx = costs.index(min_cost)
    balance_idx = norm_distances.index(min(norm_distances))

    # Build label map (a candidate can hold multiple labels)
    label_map: dict[int, list[str]] = {}
    for idx, role in [
        (fastest_idx, "Fastest"),
        (cheapest_idx, "Cheapest"),
        (balance_idx, "Best balance"),
    ]:
        label_map.setdefault(idx, []).append(role)

    points: list[ParetoPoint] = []
    for idx, candidate in enumerate(pareto):
        roles = label_map.get(idx)
        label = " / ".join(roles) if roles else None
        points.append(
            ParetoPoint(
                candidate=candidate,
                total_cost=candidate.evaluation.total_cost_usd,
                makespan=candidate.evaluation.makespan_seconds,
                label=label,
            )
        )
    return points


# ─── Main optimizer ───────────────────────────────────────────────────────────


class WorkflowOptimizerService:
    """
    Multi-cloud Pareto-optimal instance sweep for a validated workflow.

    Follows the asyncio.gather + graceful-degradation pattern from
    CostComparisonService: one provider failing does not abort the entire sweep.
    """

    # ── Step 1: Provider fetch coroutines ─────────────────────────────────────

    async def _fetch_aws_candidates(
        self,
        region: str,
        peak_vcpu: int,
        peak_ram_gb: float,
        client: httpx.AsyncClient | None,
    ) -> list[AWSEC2InstancePrice]:
        aws_region = resolve_aws_region(region)
        all_instances = await aws_pricing_service.fetch_price_list(aws_region, client=client)
        return _shortlist_aws(all_instances, peak_vcpu, peak_ram_gb)

    async def _fetch_azure_candidates(
        self,
        region: str,
        peak_vcpu: int,
        peak_ram_gb: float,
        client: httpx.AsyncClient | None,
    ) -> list[AzureVMInstancePrice]:
        azure_region = resolve_azure_region(region)
        all_instances = await azure_pricing_service.fetch_price_list(azure_region, client=client)
        return _shortlist_azure(all_instances, peak_vcpu, peak_ram_gb)

    async def _fetch_gcp_candidates(
        self,
        region: str,
        peak_vcpu: int,
        peak_ram_gb: float,
    ) -> list[GCPInstancePrice]:
        gcp_region = resolve_gcp_region(region)
        all_instances, _is_static = await gcp_pricing_service.fetch_price_list(gcp_region)
        return _shortlist_gcp(all_instances, peak_vcpu, peak_ram_gb)

    # ── Step 2: Evaluate a single candidate ───────────────────────────────────

    @staticmethod
    def _evaluate_candidate(
        provider: str,
        instance_type: str,
        vcpu: int,
        ram_gb: float,
        hourly_price: float,
        workflow: WorkflowResponse,
    ) -> CandidateResult:
        """
        Build InstanceSpec and call evaluate_workflow for one candidate.
        Returns a CandidateResult with provider_error set on incompatibility.
        """
        spec = InstanceSpec(
            vcpu=vcpu,
            ram_gb=ram_gb,
            hourly_price_usd=hourly_price,
            has_gpu=_has_gpu(instance_type),
        )
        try:
            evaluation: WorkflowEvaluation = evaluate_workflow(workflow, spec)
            return CandidateResult(
                provider=provider,
                instance_type=instance_type,
                instance_spec=spec,
                evaluation=evaluation,
                provider_error=None,
            )
        except WorkflowEvaluationError as exc:
            # All tasks incompatible — record but exclude from Pareto
            dummy_eval = WorkflowEvaluation(
                makespan_seconds=0.0,
                total_cost_usd=0.0,
                task_evaluations=[],
                incompatible_tasks=[t.id for t in workflow.tasks],
            )
            return CandidateResult(
                provider=provider,
                instance_type=instance_type,
                instance_spec=spec,
                evaluation=dummy_eval,
                provider_error=str(exc),
            )

    # ── Step 3: Top-level sweep ───────────────────────────────────────────────

    async def optimize(
        self,
        workflow: WorkflowResponse,
        region: str = "us-east",
        client: httpx.AsyncClient | None = None,
    ) -> WorkflowOptimizeResult:
        """
        Run a Pareto-optimal multi-cloud instance sweep for the given workflow.

        Args:
            workflow: Validated WorkflowResponse from WorkflowService.
            region:   Logical region key (e.g. 'us-east', 'eu-west').
            client:   Optional shared httpx.AsyncClient (injected for testing).

        Returns:
            WorkflowOptimizeResult with labelled Pareto front, all candidates,
            and any provider errors encountered.
        """
        tasks = workflow.tasks
        if not tasks:
            return WorkflowOptimizeResult(
                pareto_front=[],
                all_candidates=[],
                provider_errors=[],
                candidates_evaluated=0,
                candidates_pareto=0,
            )

        # Peak resource demand across all tasks (conservative sizing)
        peak_vcpu: int = max(t.baseline_vcpu for t in tasks)
        peak_ram_gb: float = max(t.baseline_ram_gb for t in tasks)

        logger.info(
            f"workflow_optimizer_starting region={region} "
            f"peak_vcpu={peak_vcpu} peak_ram_gb={peak_ram_gb} tasks={len(tasks)}"
        )

        # ── Concurrent provider fetches ────────────────────────────────────────
        fetch_aws = self._fetch_aws_candidates(region, peak_vcpu, peak_ram_gb, client)
        fetch_azure = self._fetch_azure_candidates(region, peak_vcpu, peak_ram_gb, client)
        fetch_gcp = self._fetch_gcp_candidates(region, peak_vcpu, peak_ram_gb)

        raw_results = await asyncio.gather(
            fetch_aws, fetch_azure, fetch_gcp, return_exceptions=True
        )

        # Provider name ↔ result index
        provider_names = ["aws", "azure", "gcp"]
        provider_errors: list[str] = []

        aws_candidates: list[AWSEC2InstancePrice] = []
        azure_candidates: list[AzureVMInstancePrice] = []
        gcp_candidates: list[GCPInstancePrice] = []

        for prov, result in zip(provider_names, raw_results, strict=True):
            if isinstance(result, BaseException):
                logger.warning(f"workflow_optimizer_provider_failed provider={prov} err={result}")
                provider_errors.append(prov)
            elif prov == "aws":
                aws_candidates = result  # type: ignore[assignment]
            elif prov == "azure":
                azure_candidates = result  # type: ignore[assignment]
            elif prov == "gcp":
                gcp_candidates = result  # type: ignore[assignment]

        # ── Evaluate all candidates ────────────────────────────────────────────
        all_results: list[CandidateResult] = []

        for aws_inst in aws_candidates:
            r = self._evaluate_candidate(
                "aws",
                aws_inst.instance_type,
                aws_inst.vcpus,
                aws_inst.memory_gb,
                aws_inst.price_per_hour_usd,
                workflow,
            )
            all_results.append(r)

        for az_inst in azure_candidates:
            r = self._evaluate_candidate(
                "azure",
                az_inst.arm_sku_name,
                az_inst.vcpus,
                az_inst.memory_gb,
                az_inst.price_per_hour_usd,
                workflow,
            )
            all_results.append(r)

        for gcp_inst in gcp_candidates:
            r = self._evaluate_candidate(
                "gcp",
                gcp_inst.machine_type,
                gcp_inst.vcpus,
                gcp_inst.memory_gb,
                gcp_inst.price_per_hour_usd,
                workflow,
            )
            all_results.append(r)

        logger.info(
            f"workflow_optimizer_evaluated total={len(all_results)} "
            f"errors={len(provider_errors)}"
        )

        # ── Pareto filtering ───────────────────────────────────────────────────
        # Exclude candidates where all tasks were incompatible
        evaluable = [r for r in all_results if r.provider_error is None]
        pareto_candidates = compute_pareto_front(evaluable)
        pareto_points = label_pareto_front(pareto_candidates)

        ai_summary = _generate_ai_summary(workflow, pareto_points, len(all_results))

        logger.info(
            f"workflow_optimizer_done pareto_size={len(pareto_points)} "
            f"total_evaluated={len(all_results)}"
        )

        return WorkflowOptimizeResult(
            pareto_front=pareto_points,
            all_candidates=all_results,
            provider_errors=provider_errors,
            candidates_evaluated=len(all_results),
            candidates_pareto=len(pareto_points),
            ai_summary=ai_summary,
        )


def _generate_ai_summary(
    workflow: WorkflowResponse,
    pareto_points: list[ParetoPoint],
    total_evaluated: int,
) -> str:
    """
    Generate a plain-language summary of the Pareto trade-offs across cloud providers.
    """
    if not pareto_points:
        return (
            "No compatible cloud instances were found matching the resource requirements "
            "of this workflow across AWS, Azure, and GCP."
        )

    fastest = next(
        (p for p in pareto_points if p.label and "Fastest" in p.label),
        pareto_points[-1],
    )
    cheapest = next(
        (p for p in pareto_points if p.label and "Cheapest" in p.label),
        pareto_points[0],
    )
    balanced = next(
        (p for p in pareto_points if p.label and "Best balance" in p.label),
        pareto_points[0],
    )

    cost_diff = fastest.total_cost - cheapest.total_cost
    time_diff = cheapest.makespan - fastest.makespan

    lines = [
        (
            f"Evaluated {total_evaluated} candidate instances across AWS, Azure, and GCP, "
            f"discovering {len(pareto_points)} Pareto-optimal deployment configurations."
        ),
        (
            f"• Cheapest: {cheapest.candidate.provider.upper()} {cheapest.candidate.instance_type} "
            f"(${cheapest.total_cost:.4f}, makespan {cheapest.makespan:.1f}s)."
        ),
        (
            f"• Fastest: {fastest.candidate.provider.upper()} {fastest.candidate.instance_type} "
            f"(${fastest.total_cost:.4f}, makespan {fastest.makespan:.1f}s)."
        ),
    ]

    if balanced != cheapest and balanced != fastest:
        lines.append(
            f"• Best Balance: {balanced.candidate.provider.upper()} "
            f"{balanced.candidate.instance_type} (${balanced.total_cost:.4f}, "
            f"makespan {balanced.makespan:.1f}s) delivers the most balanced "
            f"trade-off between cost efficiency and runtime speed."
        )
    elif cost_diff > 0 and time_diff > 0:
        pct_speedup = (time_diff / cheapest.makespan) * 100
        lines.append(
            f"Selecting the Fastest option provides a {pct_speedup:.0f}% speedup "
            f"({time_diff:.1f}s faster) for an additional ${cost_diff:.4f} in compute cost."
        )

    return "\n".join(lines)


# Module-level singleton
workflow_optimizer_service = WorkflowOptimizerService()

__all__ = [
    "WorkflowOptimizerService",
    "workflow_optimizer_service",
    "compute_pareto_front",
    "label_pareto_front",
    "_has_gpu",
    "_shortlist_aws",
    "_shortlist_azure",
    "_shortlist_gcp",
    "TOP_N_PER_PROVIDER",
]
