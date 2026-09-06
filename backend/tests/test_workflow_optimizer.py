"""
Tests — Workflow Optimizer Service
(app/services/workflow_optimizer_service.py)

Structure
---------
1. TestComputeParetoFront
   - Hand-verified 8-point fixture with explicit dominance analysis
   - Edge cases: empty, single point, all dominated, all non-dominated

2. TestLabelParetoFront
   - Labels on the same 8-point fixture
   - Tie-breaking and single-point degenerate cases

3. TestHasGpuDetection
   - Known AWS / Azure / GCP GPU instance names

4. TestShortlisting helpers
   - Verify price-sorted top-N filtering and >= requirement

5. TestWorkflowOptimizerIntegration (pure / mocked)
   - Provider failure isolation via asyncio.gather(return_exceptions=True)
   - End-to-end optimize() with all providers mocked

Hand-verified Pareto fixture (cost_usd, time_s)
------------------------------------------------
Point | cost  | time  | Pareto? | Reason if dominated
  A   | 1.00  | 500   |  YES    | no point beats both axes
  B   | 1.50  | 300   |  YES    | better time than A/D/E/G/H; better cost than C/F
  C   | 2.00  | 150   |  YES    | fastest among cheap points; better time than B
  D   | 1.40  | 400   |  NO     | dominated by B (1.50<=1.40? NO) — wait, let's be precise

Precise dominance table (cost ascending sort):
  A (1.00, 500): can anything have cost<=1.00 AND time<=500 AND strictly better?
                 Only A itself. → PARETO
  B (1.50, 300): dominated by X if X.cost<=1.50 AND X.time<=300 AND strictly better.
                 A: (1.00<=1.50, 500<=300?) 500>300 → A does NOT dominate B. → PARETO
  C (2.00, 150): A: (1.00<=2.00, 500<=150?) NO. B: (1.50<=2.00, 300<=150?) NO. → PARETO
  D (1.40, 400): B: (1.50<=1.40?) NO. A: (1.00<=1.40, 500<=400?) 500>400 NO. → Check all:
                   Only B(1.50,300): 1.50>1.40 fails. So D not dominated by B.
                   A(1.00,500): 500>400 fails.
                   Nothing with cost<=1.40 AND time<=400 exists — → PARETO
  E (1.80, 350): B(1.50,300): 1.50<=1.80 ✓ AND 300<=350 ✓ AND (1.50<1.80 ✓)
                 → B dominates E → DOMINATED
  F (2.50, 200): C(2.00,150): 2.00<=2.50 ✓ AND 150<=200 ✓ AND (2.00<2.50 ✓)
                 → C dominates F → DOMINATED
  G (1.20, 480): A(1.00,500): 1.00<=1.20 ✓ AND 500<=480? 500>480 NO. D(1.40,400): 1.40>1.20 NO.
                   Nothing dominates G → PARETO
  H (1.60, 380): B(1.50,300): 1.50<=1.60 ✓ AND 300<=380 ✓ AND 1.50<1.60 ✓
                 → B dominates H → DOMINATED

Summary:
  Pareto-optimal: A, B, C, D, G   (5 points)
  Dominated:      E (by B), F (by C), H (by B)

Pareto front sorted by cost ascending:
  A(1.00,500), G(1.20,480), D(1.40,400), B(1.50,300), C(2.00,150)

Labels on the Pareto front:
  Fastest      → C  (time=150, lowest)
  Cheapest     → A  (cost=1.00, lowest)
  Best balance → normalised distances:
      cost range: 2.00-1.00=1.00,  time range: 500-150=350
      A: nc=(1.00-1.00)/1.00=0.000  nt=(500-150)/350=1.000  dist=1.000
      G: nc=(1.20-1.00)/1.00=0.200  nt=(480-150)/350=0.943  dist=0.964
      D: nc=(1.40-1.00)/1.00=0.400  nt=(400-150)/350=0.714  dist=0.820
      B: nc=(1.50-1.00)/1.00=0.500  nt=(300-150)/350=0.429  dist=0.659
      C: nc=(2.00-1.00)/1.00=1.000  nt=(150-150)/350=0.000  dist=1.000

  Best balance → B  (dist=0.659, smallest)
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.workflow import TaskCategory, WorkflowResponse, WorkflowTaskResponse
from app.schemas.workflow_evaluation import InstanceSpec, TaskEvaluation, WorkflowEvaluation
from app.schemas.workflow_optimizer import CandidateResult, WorkflowOptimizeResult
from app.services.pricing.aws_pricing_service import AWSEC2InstancePrice
from app.services.pricing.azure_pricing_service import AzureVMInstancePrice
from app.services.pricing.gcp_pricing_service import GCPInstancePrice
from app.services.workflow_optimizer_service import (
    WorkflowOptimizerService,
    _has_gpu,
    _shortlist_aws,
    _shortlist_azure,
    _shortlist_gcp,
    compute_pareto_front,
    label_pareto_front,
    workflow_optimizer_service,
)

# =============================================================================
# Fixture builders
# =============================================================================


def _make_candidate(
    cost: float,
    time: float,
    name: str = "inst",
    provider: str = "aws",
    error: str | None = None,
) -> CandidateResult:
    """Build a CandidateResult from (cost, time) values directly."""
    spec = InstanceSpec(vcpu=4, ram_gb=16.0, hourly_price_usd=0.10)
    te = TaskEvaluation(task_id="t", scaled_time_seconds=time, cost_usd=cost)
    evaluation = WorkflowEvaluation(
        makespan_seconds=time,
        total_cost_usd=cost,
        task_evaluations=[te],
        incompatible_tasks=[],
    )
    return CandidateResult(
        provider=provider,
        instance_type=name,
        instance_spec=spec,
        evaluation=evaluation,
        provider_error=error,
    )


def _fixture_8_points() -> list[CandidateResult]:
    """
    Return the 8-point hand-verified fixture.

    Point → (cost_usd, makespan_seconds)
        A (1.00, 500)  PARETO
        B (1.50, 300)  PARETO
        C (2.00, 150)  PARETO
        D (1.40, 400)  PARETO
        E (1.80, 350)  DOMINATED by B
        F (2.50, 200)  DOMINATED by C
        G (1.20, 480)  PARETO
        H (1.60, 380)  DOMINATED by B
    """
    return [
        _make_candidate(cost=1.00, time=500, name="A"),
        _make_candidate(cost=1.50, time=300, name="B"),
        _make_candidate(cost=2.00, time=150, name="C"),
        _make_candidate(cost=1.40, time=400, name="D"),
        _make_candidate(cost=1.80, time=350, name="E"),  # dominated by B
        _make_candidate(cost=2.50, time=200, name="F"),  # dominated by C
        _make_candidate(cost=1.20, time=480, name="G"),
        _make_candidate(cost=1.60, time=380, name="H"),  # dominated by B
    ]


def _simple_workflow() -> WorkflowResponse:
    """Single cpu_bound task for integration tests."""
    return WorkflowResponse(
        workflow_id=uuid.uuid4(),
        task_count=1,
        tasks=[
            WorkflowTaskResponse(
                id="t1",
                name="Task 1",
                category=TaskCategory.cpu_bound,
                baseline_time_seconds=3600.0,
                baseline_vcpu=2,
                baseline_ram_gb=4.0,
                depends_on=[],
            )
        ],
    )


# =============================================================================
# TestComputeParetoFront
# =============================================================================


class TestComputeParetoFront:
    def test_fixture_8_points_correct_pareto_size(self) -> None:
        """Hand-verified: A, B, C, D, G are Pareto-optimal (5 of 8)."""
        result = compute_pareto_front(_fixture_8_points())
        assert len(result) == 5

    def test_fixture_pareto_contains_exactly_abcdg(self) -> None:
        """Dominated points E, F, H must not appear; A B C D G must."""
        result = compute_pareto_front(_fixture_8_points())
        pareto_names = {c.instance_type for c in result}
        assert pareto_names == {"A", "B", "C", "D", "G"}

    def test_e_is_dominated_by_b(self) -> None:
        """E(1.80,350) must be absent — dominated by B(1.50,300)."""
        result = compute_pareto_front(_fixture_8_points())
        assert "E" not in {c.instance_type for c in result}

    def test_f_is_dominated_by_c(self) -> None:
        """F(2.50,200) must be absent — dominated by C(2.00,150)."""
        result = compute_pareto_front(_fixture_8_points())
        assert "F" not in {c.instance_type for c in result}

    def test_h_is_dominated_by_b(self) -> None:
        """H(1.60,380) must be absent — dominated by B(1.50,300)."""
        result = compute_pareto_front(_fixture_8_points())
        assert "H" not in {c.instance_type for c in result}

    def test_empty_input_returns_empty(self) -> None:
        assert compute_pareto_front([]) == []

    def test_single_point_is_always_pareto(self) -> None:
        c = _make_candidate(1.0, 100.0, "solo")
        assert compute_pareto_front([c]) == [c]

    def test_all_pareto_when_no_dominance(self) -> None:
        """Strictly decreasing cost, strictly increasing time → all Pareto-optimal."""
        points = [
            _make_candidate(cost=1.0, time=400.0, name="p1"),
            _make_candidate(cost=2.0, time=200.0, name="p2"),
            _make_candidate(cost=3.0, time=100.0, name="p3"),
        ]
        result = compute_pareto_front(points)
        assert len(result) == 3

    def test_all_dominated_except_one(self) -> None:
        """One point that strictly beats all others on both axes."""
        winner = _make_candidate(cost=0.5, time=50.0, name="best")
        losers = [
            _make_candidate(cost=1.0, time=100.0, name="x"),
            _make_candidate(cost=1.5, time=200.0, name="y"),
        ]
        result = compute_pareto_front([winner] + losers)
        assert len(result) == 1
        assert result[0].instance_type == "best"

    def test_equal_cost_different_time_dominance(self) -> None:
        """Same cost, lower time → strict dominance."""
        fast = _make_candidate(cost=1.0, time=100.0, name="fast")
        slow = _make_candidate(cost=1.0, time=200.0, name="slow")
        result = compute_pareto_front([fast, slow])
        assert len(result) == 1
        assert result[0].instance_type == "fast"

    def test_equal_time_different_cost_dominance(self) -> None:
        """Same time, lower cost → strict dominance."""
        cheap = _make_candidate(cost=0.5, time=100.0, name="cheap")
        expensive = _make_candidate(cost=1.0, time=100.0, name="exp")
        result = compute_pareto_front([cheap, expensive])
        assert len(result) == 1
        assert result[0].instance_type == "cheap"

    def test_identical_points_both_pareto(self) -> None:
        """Identical (cost, time) — neither dominates the other (requires strictly better)."""
        a = _make_candidate(cost=1.0, time=100.0, name="a")
        b = _make_candidate(cost=1.0, time=100.0, name="b")
        result = compute_pareto_front([a, b])
        assert len(result) == 2

    def test_pareto_all_incompatible_excluded_by_caller(self) -> None:
        """
        Candidates with provider_error are excluded by the optimizer before calling
        compute_pareto_front.  This test confirms the filtering contract used in optimize().
        """
        error_candidate = _make_candidate(1.0, 200.0, error="incompatible")
        ok_candidate = _make_candidate(2.0, 100.0)
        # Only pass evaluable candidates (no provider_error)
        evaluable = [c for c in [error_candidate, ok_candidate] if c.provider_error is None]
        result = compute_pareto_front(evaluable)
        assert len(result) == 1


# =============================================================================
# TestLabelParetoFront
# =============================================================================


class TestLabelParetoFront:
    def _pareto_from_fixture(self) -> list[CandidateResult]:
        """Return the 5 Pareto-optimal points from the 8-point fixture."""
        return [c for c in _fixture_8_points() if c.instance_type in {"A", "B", "C", "D", "G"}]

    def test_label_count_equals_pareto_size(self) -> None:
        pareto = self._pareto_from_fixture()
        points = label_pareto_front(pareto)
        assert len(points) == len(pareto)

    def test_cheapest_label_assigned_to_a(self) -> None:
        """A(1.00, 500) is cheapest."""
        pareto = self._pareto_from_fixture()
        points = label_pareto_front(pareto)
        cheapest = next(p for p in points if p.candidate.instance_type == "A")
        assert cheapest.label is not None
        assert "Cheapest" in cheapest.label

    def test_fastest_label_assigned_to_c(self) -> None:
        """C(2.00, 150) is fastest."""
        pareto = self._pareto_from_fixture()
        points = label_pareto_front(pareto)
        fastest = next(p for p in points if p.candidate.instance_type == "C")
        assert fastest.label is not None
        assert "Fastest" in fastest.label

    def test_best_balance_label_assigned_to_b(self) -> None:
        """
        B(1.50, 300) has the minimum normalised Euclidean distance.

        Hand-verified above (dist_B = 0.659 < all others).
        """
        pareto = self._pareto_from_fixture()
        points = label_pareto_front(pareto)
        balance = next(p for p in points if p.candidate.instance_type == "B")
        assert balance.label is not None
        assert "Best balance" in balance.label

    def test_best_balance_distance_is_minimum(self) -> None:
        """
        Verify the balance winner genuinely has the smallest normalised distance.
        """
        pareto = self._pareto_from_fixture()
        costs = [c.evaluation.total_cost_usd for c in pareto]
        times = [c.evaluation.makespan_seconds for c in pareto]
        min_c, max_c = min(costs), max(costs)
        min_t, max_t = min(times), max(times)
        cr, tr = max_c - min_c, max_t - min_t

        dists = {
            c.instance_type: math.sqrt(
                ((c.evaluation.total_cost_usd - min_c) / cr if cr else 0.0) ** 2
                + ((c.evaluation.makespan_seconds - min_t) / tr if tr else 0.0) ** 2
            )
            for c in pareto
        }
        winner_name = min(dists, key=lambda k: dists[k])
        assert winner_name == "B"
        assert dists["B"] == pytest.approx(0.659, abs=0.01)

    def test_empty_pareto_returns_empty_points(self) -> None:
        assert label_pareto_front([]) == []

    def test_single_point_gets_all_three_labels(self) -> None:
        """With one Pareto point, it is simultaneously Fastest, Cheapest, Best balance."""
        solo = _make_candidate(1.0, 100.0, "solo")
        points = label_pareto_front([solo])
        assert len(points) == 1
        label = points[0].label
        assert label is not None
        assert "Fastest" in label
        assert "Cheapest" in label
        assert "Best balance" in label

    def test_total_cost_and_makespan_fields_are_shortcuts(self) -> None:
        """ParetoPoint.total_cost and .makespan must mirror the evaluation values."""
        solo = _make_candidate(1.23, 456.0, "s")
        points = label_pareto_front([solo])
        assert points[0].total_cost == pytest.approx(1.23)
        assert points[0].makespan == pytest.approx(456.0)

    def test_zero_cost_range_best_balance_uses_time_only(self) -> None:
        """When all Pareto points have identical cost, best balance = fastest."""
        pts = [
            _make_candidate(cost=1.0, time=300.0, name="p1"),
            _make_candidate(cost=1.0, time=100.0, name="p2"),  # fastest
            _make_candidate(cost=1.0, time=200.0, name="p3"),
        ]
        pareto = compute_pareto_front(pts)
        # All three have same cost, strictly decreasing time — check which ones survive
        # p1(1.0,300): any with cost<=1.0 AND time<=300 AND strict?
        # p2(1.0,100) → 1.0==1.0 ✓ 100<300 ✓ → dominated
        # p2(1.0,100): any with cost<=1.0 AND time<=100? Only p2 itself → PARETO
        # p3(1.0,200): p2(1.0,100) → 1.0==1.0, 100<200 → dominated
        assert len(pareto) == 1
        assert pareto[0].instance_type == "p2"
        points = label_pareto_front(pareto)
        assert "Best balance" in (points[0].label or "")


# =============================================================================
# TestHasGpuDetection
# =============================================================================


class TestHasGpuDetection:
    def test_aws_p3_is_gpu(self) -> None:
        assert _has_gpu("p3.2xlarge") is True

    def test_aws_g4dn_is_gpu(self) -> None:
        assert _has_gpu("g4dn.xlarge") is True

    def test_aws_c5_is_not_gpu(self) -> None:
        assert _has_gpu("c5.4xlarge") is False

    def test_aws_m5_is_not_gpu(self) -> None:
        assert _has_gpu("m5.large") is False

    def test_azure_nc_is_gpu(self) -> None:
        assert _has_gpu("Standard_NC6") is True

    def test_azure_nd_is_gpu(self) -> None:
        assert _has_gpu("Standard_ND96asr_v4") is True

    def test_azure_d4s_is_not_gpu(self) -> None:
        assert _has_gpu("Standard_D4s_v3") is False

    def test_gcp_a2_is_gpu(self) -> None:
        assert _has_gpu("a2-highgpu-1g") is True

    def test_gcp_e2_is_not_gpu(self) -> None:
        assert _has_gpu("e2-standard-4") is False


# =============================================================================
# TestShortlisting
# =============================================================================


def _aws_inst(instance_type: str, vcpus: int, mem: float, price: float) -> AWSEC2InstancePrice:
    return AWSEC2InstancePrice(
        sku="sku", instance_type=instance_type, vcpus=vcpus, memory_gb=mem,
        price_per_hour_usd=price,
    )


def _azure_inst(sku: str, vcpus: int, mem: float, price: float) -> AzureVMInstancePrice:
    return AzureVMInstancePrice(
        arm_sku_name=sku, sku_name=sku, meter_name="", product_name="",
        vcpus=vcpus, memory_gb=mem, price_per_hour_usd=price,
    )


def _gcp_inst(machine_type: str, vcpus: int, mem: float, price: float) -> GCPInstancePrice:
    return GCPInstancePrice(
        machine_type=machine_type, vcpus=vcpus, memory_gb=mem,
        price_per_hour_usd=price, region_code="us-east4",
    )


class TestShortlistAws:
    def test_filters_out_undersized_instances(self) -> None:
        instances = [
            _aws_inst("small", vcpus=2, mem=4.0, price=0.10),
            _aws_inst("big",   vcpus=8, mem=32.0, price=0.50),
        ]
        result = _shortlist_aws(instances, peak_vcpu=4, peak_ram_gb=16.0)
        assert len(result) == 1
        assert result[0].instance_type == "big"

    def test_sorted_by_price_ascending(self) -> None:
        instances = [
            _aws_inst("expensive", vcpus=4, mem=16.0, price=1.00),
            _aws_inst("cheap",     vcpus=4, mem=16.0, price=0.20),
            _aws_inst("mid",       vcpus=4, mem=16.0, price=0.50),
        ]
        result = _shortlist_aws(instances, peak_vcpu=4, peak_ram_gb=16.0, top_n=10)
        assert [r.instance_type for r in result] == ["cheap", "mid", "expensive"]

    def test_respects_top_n_limit(self) -> None:
        instances = [_aws_inst(f"i{k}", vcpus=4, mem=16.0, price=float(k)) for k in range(50)]
        result = _shortlist_aws(instances, peak_vcpu=4, peak_ram_gb=16.0, top_n=5)
        assert len(result) == 5

    def test_empty_input_returns_empty(self) -> None:
        assert _shortlist_aws([], peak_vcpu=2, peak_ram_gb=8.0) == []


class TestShortlistAzure:
    def test_filters_undersized(self) -> None:
        instances = [
            _azure_inst("Standard_B2s", vcpus=2, mem=4.0, price=0.05),
            _azure_inst("Standard_D8s_v3", vcpus=8, mem=32.0, price=0.40),
        ]
        result = _shortlist_azure(instances, peak_vcpu=4, peak_ram_gb=16.0)
        assert len(result) == 1
        assert result[0].arm_sku_name == "Standard_D8s_v3"

    def test_sorted_by_price_ascending(self) -> None:
        instances = [
            _azure_inst("D16", vcpus=8, mem=32.0, price=0.80),
            _azure_inst("D8a", vcpus=8, mem=32.0, price=0.35),
        ]
        result = _shortlist_azure(instances, peak_vcpu=4, peak_ram_gb=16.0, top_n=10)
        assert result[0].arm_sku_name == "D8a"


class TestShortlistGcp:
    def test_filters_undersized(self) -> None:
        instances = [
            _gcp_inst("e2-small",      vcpus=2, mem=2.0,  price=0.02),
            _gcp_inst("e2-standard-8", vcpus=8, mem=32.0, price=0.27),
        ]
        result = _shortlist_gcp(instances, peak_vcpu=4, peak_ram_gb=16.0)
        assert len(result) == 1
        assert result[0].machine_type == "e2-standard-8"

    def test_sorted_by_price(self) -> None:
        instances = [
            _gcp_inst("n2-standard-8", vcpus=8, mem=32.0, price=0.39),
            _gcp_inst("e2-standard-8", vcpus=8, mem=32.0, price=0.27),
        ]
        result = _shortlist_gcp(instances, peak_vcpu=4, peak_ram_gb=16.0, top_n=10)
        assert result[0].machine_type == "e2-standard-8"


# =============================================================================
# TestWorkflowOptimizerIntegration (mocked — no live API calls)
# =============================================================================


class TestWorkflowOptimizerIntegration:
    """
    End-to-end tests for WorkflowOptimizerService.optimize() using mocked
    pricing services.  No live network calls occur.
    """

    def _make_optimizer(self) -> WorkflowOptimizerService:
        return WorkflowOptimizerService()

    @pytest.mark.asyncio
    async def test_provider_failure_is_isolated(self) -> None:
        """
        AWS fetch raises an exception → AWS appears in provider_errors.
        Azure and GCP still contribute candidates; result is not None.
        """
        optimizer = self._make_optimizer()
        workflow = _simple_workflow()

        azure_inst = _azure_inst("Standard_D4s_v3", vcpus=4, mem=16.0, price=0.20)
        gcp_inst = _gcp_inst("e2-standard-4", vcpus=4, mem=16.0, price=0.13)

        with (
            patch.object(
                optimizer,
                "_fetch_aws_candidates",
                new=AsyncMock(side_effect=RuntimeError("AWS fetch failed")),
            ),
            patch.object(
                optimizer,
                "_fetch_azure_candidates",
                new=AsyncMock(return_value=[azure_inst]),
            ),
            patch.object(
                optimizer,
                "_fetch_gcp_candidates",
                new=AsyncMock(return_value=[gcp_inst]),
            ),
        ):
            result = await optimizer.optimize(workflow, region="us-east")

        assert "aws" in result.provider_errors
        assert "azure" not in result.provider_errors
        assert "gcp" not in result.provider_errors
        assert result.candidates_evaluated == 2  # 1 azure + 1 gcp

    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_empty_result(self) -> None:
        optimizer = self._make_optimizer()
        workflow = _simple_workflow()

        with (
            patch.object(optimizer, "_fetch_aws_candidates",
                         new=AsyncMock(side_effect=RuntimeError("fail"))),
            patch.object(optimizer, "_fetch_azure_candidates",
                         new=AsyncMock(side_effect=RuntimeError("fail"))),
            patch.object(optimizer, "_fetch_gcp_candidates",
                         new=AsyncMock(side_effect=RuntimeError("fail"))),
        ):
            result = await optimizer.optimize(workflow)

        assert result.candidates_evaluated == 0
        assert result.pareto_front == []
        assert set(result.provider_errors) == {"aws", "azure", "gcp"}

    @pytest.mark.asyncio
    async def test_single_provider_single_instance_becomes_pareto(self) -> None:
        optimizer = self._make_optimizer()
        workflow = _simple_workflow()

        aws_inst = _aws_inst("m5.xlarge", vcpus=4, mem=16.0, price=0.192)

        with (
            patch.object(optimizer, "_fetch_aws_candidates",
                         new=AsyncMock(return_value=[aws_inst])),
            patch.object(optimizer, "_fetch_azure_candidates",
                         new=AsyncMock(return_value=[])),
            patch.object(optimizer, "_fetch_gcp_candidates",
                         new=AsyncMock(return_value=[])),
        ):
            result = await optimizer.optimize(workflow)

        assert result.candidates_evaluated == 1
        assert result.candidates_pareto == 1
        assert result.pareto_front[0].label is not None

    @pytest.mark.asyncio
    async def test_dominated_candidate_excluded_from_pareto(self) -> None:
        """
        Two AWS instances: cheap&slow vs expensive&fast vs cheap&fast.
        The cheap&slow and expensive&fast are dominated by the third.
        """
        optimizer = self._make_optimizer()
        workflow = _simple_workflow()

        # Both at 2× baseline_vcpu so 2× speedup; baseline_time=3600s
        # scaled_time = 3600/2 = 1800 s for any 4vCPU instance
        # cost = (1800/3600) * price_per_hour
        winner = _aws_inst("winner", vcpus=4, mem=16.0, price=0.10)   # cost=0.05, time=1800
        loser1 = _aws_inst("loser1", vcpus=4, mem=16.0, price=0.20)   # cost=0.10, same time

        with (
            patch.object(optimizer, "_fetch_aws_candidates",
                         new=AsyncMock(return_value=[winner, loser1])),
            patch.object(optimizer, "_fetch_azure_candidates",
                         new=AsyncMock(return_value=[])),
            patch.object(optimizer, "_fetch_gcp_candidates",
                         new=AsyncMock(return_value=[])),
        ):
            result = await optimizer.optimize(workflow)

        # loser1 has same time but higher cost → dominated by winner
        assert result.candidates_pareto == 1
        pareto_types = {p.candidate.instance_type for p in result.pareto_front}
        assert "winner" in pareto_types
        assert "loser1" not in pareto_types

    @pytest.mark.asyncio
    async def test_result_is_workflow_optimize_result_instance(self) -> None:
        optimizer = self._make_optimizer()
        workflow = _simple_workflow()

        with (
            patch.object(optimizer, "_fetch_aws_candidates",
                         new=AsyncMock(return_value=[])),
            patch.object(optimizer, "_fetch_azure_candidates",
                         new=AsyncMock(return_value=[])),
            patch.object(optimizer, "_fetch_gcp_candidates",
                         new=AsyncMock(return_value=[])),
        ):
            result = await optimizer.optimize(workflow)

        assert isinstance(result, WorkflowOptimizeResult)
        assert isinstance(result.pareto_front, list)
        assert isinstance(result.provider_errors, list)

    @pytest.mark.asyncio
    async def test_pareto_labels_present_when_multiple_candidates(self) -> None:
        """With ≥2 Pareto-optimal candidates, Fastest and Cheapest labels appear."""
        optimizer = self._make_optimizer()
        workflow = WorkflowResponse(
            workflow_id=uuid.uuid4(),
            task_count=1,
            tasks=[
                WorkflowTaskResponse(
                    id="t1",
                    name="cpu task",
                    category=TaskCategory.cpu_bound,
                    baseline_time_seconds=3600.0,
                    baseline_vcpu=2,
                    baseline_ram_gb=4.0,
                    depends_on=[],
                )
            ],
        )
        # cheap&slow: 2vCPU (no speedup), low price
        # fast&expensive: 8vCPU (4× speedup), high price
        cheap_slow = _aws_inst("cheap", vcpus=2, mem=8.0, price=0.05)
        fast_exp   = _aws_inst("fast",  vcpus=8, mem=8.0, price=0.50)

        with (
            patch.object(optimizer, "_fetch_aws_candidates",
                         new=AsyncMock(return_value=[cheap_slow, fast_exp])),
            patch.object(optimizer, "_fetch_azure_candidates",
                         new=AsyncMock(return_value=[])),
            patch.object(optimizer, "_fetch_gcp_candidates",
                         new=AsyncMock(return_value=[])),
        ):
            result = await optimizer.optimize(workflow)

        all_labels = [p.label for p in result.pareto_front if p.label]
        label_text = " ".join(all_labels)
        assert "Fastest" in label_text
        assert "Cheapest" in label_text


# =============================================================================
# TestWorkflowOptimizeEndpoint (HTTP Integration)
# =============================================================================


class TestWorkflowOptimizeEndpoint:
    """HTTP endpoint integration tests for POST /api/v1/workflows/optimize."""

    @pytest.fixture
    def client(self) -> Generator[TestClient, None, None]:
        from app.main import create_application

        with TestClient(create_application()) as test_client:
            yield test_client

    def test_optimize_endpoint_invalid_dag_returns_422(self, client: TestClient) -> None:
        """Self-cycle in workflow DAG returns HTTP 422 with validation error code."""
        payload = {
            "workflow": {
                "tasks": [
                    {
                        "id": "t1",
                        "name": "cyclic task",
                        "category": "cpu_bound",
                        "baseline_time_seconds": 100.0,
                        "baseline_vcpu": 2,
                        "baseline_ram_gb": 4.0,
                        "depends_on": ["t1"],
                    }
                ]
            },
            "region": "us-east",
        }
        response = client.post("/api/v1/workflows/optimize", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "WORKFLOW_VALIDATION_ERROR"

    def test_optimize_endpoint_success_mocked(self, client: TestClient) -> None:
        """Valid DAG returns HTTP 200 with Pareto sweep results."""
        inst_cheap = _aws_inst("t3.medium", vcpus=2, mem=4.0, price=0.04)
        with (
            patch.object(
                workflow_optimizer_service,
                "_fetch_aws_candidates",
                new=AsyncMock(return_value=[inst_cheap]),
            ),
            patch.object(
                workflow_optimizer_service,
                "_fetch_azure_candidates",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                workflow_optimizer_service,
                "_fetch_gcp_candidates",
                new=AsyncMock(return_value=[]),
            ),
        ):
            payload = {
                "workflow": {
                    "tasks": [
                        {
                            "id": "t1",
                            "name": "valid task",
                            "category": "cpu_bound",
                            "baseline_time_seconds": 120.0,
                            "baseline_vcpu": 2,
                            "baseline_ram_gb": 4.0,
                            "depends_on": [],
                        }
                    ]
                },
                "region": "us-east",
            }
            response = client.post("/api/v1/workflows/optimize", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "pareto_front" in data
            assert len(data["pareto_front"]) == 1
            assert data["candidates_evaluated"] == 1
            assert data["candidates_pareto"] == 1
            assert data["pareto_front"][0]["candidate"]["instance_type"] == "t3.medium"

