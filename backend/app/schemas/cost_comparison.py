"""
Infralytix — Multi-Cloud Cost Comparison Schemas (Pydantic v2).

Defines request and response schemas for comparing resource costs
across AWS, Azure, and Google Cloud Platform.
"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CloudResourceRequest(BaseModel):
    """
    Requested cloud resource configuration for multi-cloud cost evaluation.

    Accepts both standard and alias field names for compatibility:
      - vcpu / cpu_cores: vCPU count (ge=1)
      - ram_gb / memory_gb: RAM in GB (ge=1)
      - storage_gb: persistent block storage in GB (ge=0)
      - region / region_preference: deployment region hint (e.g. 'us-east', 'us-west', 'eu-west')
      - hours_per_month: runtime hours per month (default 730 = 24x7)
    """

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    vcpu: int = Field(
        default=2,
        ge=1,
        le=256,
        validation_alias=AliasChoices("vcpu", "cpu_cores"),
        description="Number of virtual CPUs",
    )
    ram_gb: int = Field(
        default=4,
        ge=1,
        le=3904,
        validation_alias=AliasChoices("ram_gb", "memory_gb"),
        description="System memory in gigabytes",
    )
    storage_gb: int = Field(
        default=50,
        ge=0,
        le=65536,
        description="Persistent block storage in gigabytes",
    )
    region: str = Field(
        default="us-east",
        validation_alias=AliasChoices("region", "region_preference"),
        description="Target deployment region (e.g. 'us-east', 'us-west', 'eu-west')",
    )
    hours_per_month: int = Field(
        default=730,
        ge=1,
        le=744,
        description="Expected monthly runtime hours (default 730)",
    )


class CloudCostEstimate(BaseModel):
    """
    Cost estimate result for a single cloud provider.
    """

    model_config = ConfigDict(populate_by_name=True)

    provider: str = Field(..., description="Cloud provider identifier ('aws', 'azure', 'gcp')")
    instance_type_matched: str = Field(
        ..., description="Matched VM machine type or SKU name, or 'unavailable' on error"
    )
    monthly_cost_low: float = Field(
        ..., description="Lower estimate or baseline monthly cost in USD"
    )
    monthly_cost_high: float = Field(
        ..., description="Upper estimate or on-demand monthly cost in USD"
    )
    currency: str = Field(default="USD", description="Billing currency ISO code")
    notes: str | None = Field(default=None, description="Disclaimers or notes")
    error: str | None = Field(default=None, description="Error message if pricing query failed")


class CloudComparisonResponse(BaseModel):
    """
    Comprehensive multi-cloud cost comparison response.
    """

    model_config = ConfigDict(populate_by_name=True)

    estimates: list[CloudCostEstimate] = Field(
        ..., description="Cost estimates for each evaluated cloud provider"
    )
    ai_suggestion: str = Field(
        ..., description="AI-generated recommendation or contextual comparison insight"
    )


__all__ = [
    "CloudResourceRequest",
    "CloudCostEstimate",
    "CloudComparisonResponse",
]
