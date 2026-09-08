"""
Infralytix — Workflow Optimizer Schemas (Pydantic v2).

Defines the input (WorkflowOptimizeRequest) and output structures
for the Pareto-optimal multi-cloud instance sweep.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.workflow import WorkflowCreateRequest
from app.schemas.workflow_evaluation import InstanceSpec, WorkflowEvaluation

# ─── Per-candidate result ─────────────────────────────────────────────────────


class CandidateResult(BaseModel):
    """
    Evaluation of a single (provider, instance) candidate against the workflow.

    Attributes:
        provider:          Cloud provider identifier ('aws' | 'azure' | 'gcp').
        instance_type:     Provider-specific instance type string.
        instance_spec:     Full InstanceSpec used for evaluation.
        evaluation:        WorkflowEvaluation output (makespan, cost, task breakdown).
        provider_error:    Non-None if this candidate's provider fetch failed; the
                           candidate is then excluded from Pareto analysis.
    """

    provider: str = Field(..., description="Cloud provider ('aws' | 'azure' | 'gcp').")
    instance_type: str = Field(..., description="Provider instance type name.")
    instance_spec: InstanceSpec = Field(..., description="Instance specification used.")
    evaluation: WorkflowEvaluation = Field(..., description="Workflow evaluation result.")
    provider_error: str | None = Field(
        default=None,
        description="Error message if this candidate's provider data was unavailable.",
    )


# ─── Pareto point ─────────────────────────────────────────────────────────────


class ParetoPoint(BaseModel):
    """
    A single Pareto-optimal (cost, time) point with its associated candidate.

    Attributes:
        candidate:     The full CandidateResult.
        total_cost:    Shortcut from candidate.evaluation.total_cost_usd.
        makespan:      Shortcut from candidate.evaluation.makespan_seconds.
        label:         Optional label: 'Fastest' | 'Cheapest' | 'Best balance' | None.
    """

    candidate: CandidateResult
    total_cost: float = Field(..., ge=0, description="Total workflow cost in USD.")
    makespan: float = Field(..., ge=0, description="Critical-path makespan in seconds.")
    label: str | None = Field(
        default=None,
        description="Pareto label: 'Fastest' | 'Cheapest' | 'Best balance'.",
    )


# ─── Sweep result ─────────────────────────────────────────────────────────────


class WorkflowOptimizeResult(BaseModel):
    """
    Result of a multi-cloud Pareto sweep for a given workflow.

    Attributes:
        pareto_front:        Pareto-optimal (cost, time) candidates, labelled.
        all_candidates:      All evaluated candidates (including dominated ones).
        provider_errors:     Providers that failed to return pricing data.
        candidates_evaluated: Total number of (provider, instance) pairs evaluated.
        candidates_pareto:   Count of Pareto-optimal points.
    """

    pareto_front: list[ParetoPoint] = Field(..., description="Pareto-optimal candidates, labelled.")
    all_candidates: list[CandidateResult] = Field(
        ..., description="All evaluated candidates (dominated and non-dominated)."
    )
    provider_errors: list[str] = Field(
        default_factory=list,
        description="Provider names that failed to return pricing data.",
    )
    candidates_evaluated: int = Field(
        ..., ge=0, description="Total (provider, instance) pairs evaluated."
    )
    candidates_pareto: int = Field(..., ge=0, description="Number of Pareto-optimal points.")
    ai_summary: str | None = Field(
        default=None,
        description="AI-generated plain-language summary of the Pareto trade-offs.",
    )


class WorkflowOptimizeRequest(BaseModel):
    """
    Request payload for multi-cloud Pareto optimization of a workflow DAG.
    """

    workflow: WorkflowCreateRequest = Field(
        ..., description="Workflow DAG definition with task specifications."
    )
    region: str = Field(
        default="us-east",
        description="Target geographic region key (e.g., 'us-east', 'us-west', 'eu-west').",
    )


__all__ = [
    "CandidateResult",
    "ParetoPoint",
    "WorkflowOptimizeRequest",
    "WorkflowOptimizeResult",
]
