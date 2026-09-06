"""
Infralytix — Multi-Cloud Cost Comparison Schemas (Pydantic v2).

Defines request and response schemas for the cost estimation feature.
All schemas are decoupled from ORM models per project conventions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CloudProvider = Literal["aws", "gcp", "azure"]

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class CostEstimateRequest(BaseModel):
    """
    Workload specification submitted by the user.

    All resource values use common units:
      - cpu_cores: vCPU count
      - memory_gb: GB of RAM
      - storage_gb: GB of persistent block storage
      - hours_per_month: expected runtime hours (default = 730, i.e. 24x7)

    providers: subset of ["aws", "gcp", "azure"] to compare.
    region_preference: loose text hint ("us", "eu", "asia") used to pick
    the closest regional pricing tier.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    cpu_cores: Annotated[int, Field(ge=1, le=256, description="vCPU count")] = 2
    memory_gb: Annotated[int, Field(ge=1, le=3904, description="RAM in GB")] = 4
    storage_gb: Annotated[int, Field(ge=0, le=65536, description="Persistent storage in GB")] = 50
    hours_per_month: Annotated[
        float, Field(ge=1.0, le=744.0, description="Expected runtime hours/month")
    ] = 730.0
    providers: list[CloudProvider] = Field(
        default=["aws", "gcp", "azure"],
        min_length=1,
        description="Cloud providers to compare",
    )
    region_preference: Literal["us", "eu", "asia"] = Field(
        default="us",
        description="Preferred deployment region for pricing tier selection",
    )
    workload_label: str = Field(
        default="",
        max_length=120,
        description="Optional human-readable label for this estimate",
    )


# ---------------------------------------------------------------------------
# Response Sub-Schemas
# ---------------------------------------------------------------------------


class InstanceOption(BaseModel):
    """The specific VM instance type selected for a provider."""

    instance_type: str = Field(..., description="Provider-specific instance identifier")
    vcpus: int = Field(..., description="vCPUs provided by this instance")
    memory_gb: float = Field(..., description="RAM provided by this instance (GB)")
    price_per_hour_usd: float = Field(..., description="On-demand price in USD/hr")


class StorageEstimate(BaseModel):
    """Block storage cost breakdown."""

    storage_type: str = Field(..., description="Storage class (e.g. gp3, pd-balanced)")
    price_per_gb_month_usd: float = Field(..., description="Price per GB per month (USD)")
    total_cost_usd: float = Field(..., description="Monthly storage cost (USD)")


class ProviderEstimate(BaseModel):
    """
    Full cost estimate for a single cloud provider.

    Compute + storage costs are shown separately so the UI can break
    down the bill. total_monthly_usd is their sum.
    """

    provider: CloudProvider = Field(..., description="Cloud provider identifier")
    provider_display: str = Field(..., description="Human-readable provider name")
    region: str = Field(..., description="Region used for pricing")
    instance: InstanceOption = Field(..., description="Selected VM instance")
    compute_monthly_usd: float = Field(..., description="Compute cost for requested hours")
    storage: StorageEstimate = Field(..., description="Storage cost breakdown")
    total_monthly_usd: float = Field(..., description="Total estimated monthly cost (USD)")
    notes: list[str] = Field(
        default_factory=list,
        description="Caveats or assumptions for this estimate",
    )


class CostComparisonResult(BaseModel):
    """
    Aggregated multi-cloud comparison plus AI recommendation.

    providers is always sorted by total_monthly_usd ascending
    so the cheapest option appears first.
    """

    providers: list[ProviderEstimate] = Field(
        ...,
        description="Per-provider estimates, sorted cheapest-first",
    )
    cheapest_provider: CloudProvider = Field(
        ..., description="Provider with the lowest monthly total"
    )
    ai_suggestion: str = Field(
        ...,
        description=(
            "AI-generated recommendation explaining the trade-offs and which "
            "provider best fits the described workload."
        ),
    )


class CostEstimateResponse(BaseModel):
    """API response envelope for a saved cost estimate."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="AgentRun ID for this estimate")
    result: CostComparisonResult = Field(..., description="Cost comparison result")
    created_at: datetime = Field(..., description="When the estimate was computed")
    workload_label: str = Field(default="", description="Label from the original request")


class CostEstimateListItem(BaseModel):
    """Lightweight summary used in the estimate history list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cheapest_provider: str
    total_monthly_usd: float
    workload_label: str
    created_at: datetime
