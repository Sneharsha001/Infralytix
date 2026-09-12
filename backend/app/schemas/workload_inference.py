"""
Infralytix — Workload Inference Schemas (Pydantic v2).

Defines the request/response contract for the POST /projects/{id}/infer-workload
endpoint that infers compute resource requirements from a repository archive.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkloadInferenceResult(BaseModel):
    """
    Inferred compute profile for a repository workload.

    Returned by POST /api/v1/projects/{id}/infer-workload after static
    analysis and optional Gemini inference.
    """

    vcpu: int = Field(
        ...,
        ge=1,
        le=256,
        description="Estimated vCPU cores required for the workload",
    )
    ram_gb: int = Field(
        ...,
        ge=1,
        le=3904,
        description="Estimated RAM in GB required for the workload",
    )
    storage_gb: int = Field(
        ...,
        ge=1,
        le=65536,
        description="Estimated block storage in GB required for the workload",
    )
    justification: str = Field(
        ...,
        description=(
            "One-line explanation of why these resources were recommended, "
            "based on repo structure, dependency count, and primary language."
        ),
    )
