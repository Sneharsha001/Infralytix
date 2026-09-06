"""
Infralytix — Multi-Cloud Cost Calculator Service.

Provides deterministic, static-table-based price lookups for AWS, GCP,
and Azure compute + block storage.

Design decisions:
  - NO live API calls: static pricing data from public pricing pages
    (AWS on-demand us-east-1, GCP us-central1, Azure eastus — retrieved
    from official pricing pages, accurate as of 2024-Q4).
  - Instance selection: find the cheapest instance with >= requested vCPUs
    and >= requested memory from a curated catalogue of general-purpose VMs.
  - Storage: standard block storage (gp3 / pd-balanced / Premium SSD LRS).
  - All prices in USD.

This module contains ONLY business logic — no FastAPI, no SQLAlchemy,
no logging side effects. It is pure and fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.cost import (
    CostEstimateRequest,
    InstanceOption,
    ProviderEstimate,
    StorageEstimate,
)

# ---------------------------------------------------------------------------
# Static Price Catalogues
# ---------------------------------------------------------------------------
# Format: (instance_type, vcpus, memory_gb, price_per_hour_usd)
# Sources:
#   AWS    : https://aws.amazon.com/ec2/pricing/on-demand/ (us-east-1, Linux)
#   GCP    : https://cloud.google.com/compute/vm-instance-pricing (us-central1)
#   Azure  : https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/ (eastus)

@dataclass(frozen=True)
class _InstanceSpec:
    instance_type: str
    vcpus: int
    memory_gb: float
    price_per_hour_usd: float


_AWS_CATALOGUE: list[_InstanceSpec] = [
    _InstanceSpec("t3.micro",    1,   1.0,  0.0104),
    _InstanceSpec("t3.small",    2,   2.0,  0.0208),
    _InstanceSpec("t3.medium",   2,   4.0,  0.0416),
    _InstanceSpec("t3.large",    2,   8.0,  0.0832),
    _InstanceSpec("t3.xlarge",   4,  16.0,  0.1664),
    _InstanceSpec("t3.2xlarge",  8,  32.0,  0.3328),
    _InstanceSpec("m5.large",    2,   8.0,  0.0960),
    _InstanceSpec("m5.xlarge",   4,  16.0,  0.1920),
    _InstanceSpec("m5.2xlarge",  8,  32.0,  0.3840),
    _InstanceSpec("m5.4xlarge", 16,  64.0,  0.7680),
    _InstanceSpec("m5.8xlarge", 32, 128.0,  1.5360),
    _InstanceSpec("c5.large",    2,   4.0,  0.0850),
    _InstanceSpec("c5.xlarge",   4,   8.0,  0.1700),
    _InstanceSpec("c5.2xlarge",  8,  16.0,  0.3400),
    _InstanceSpec("c5.4xlarge", 16,  32.0,  0.6800),
    _InstanceSpec("r5.large",    2,  16.0,  0.1260),
    _InstanceSpec("r5.xlarge",   4,  32.0,  0.2520),
    _InstanceSpec("r5.2xlarge",  8,  64.0,  0.5040),
    _InstanceSpec("r5.4xlarge", 16, 128.0,  1.0080),
]

_GCP_CATALOGUE: list[_InstanceSpec] = [
    _InstanceSpec("e2-micro",       2,   1.0,  0.0084),
    _InstanceSpec("e2-small",       2,   2.0,  0.0134),
    _InstanceSpec("e2-medium",      2,   4.0,  0.0268),
    _InstanceSpec("e2-standard-2",  2,   8.0,  0.0670),
    _InstanceSpec("e2-standard-4",  4,  16.0,  0.1340),
    _InstanceSpec("e2-standard-8",  8,  32.0,  0.2680),
    _InstanceSpec("e2-standard-16",16,  64.0,  0.5360),
    _InstanceSpec("n2-standard-2",  2,   8.0,  0.0971),
    _InstanceSpec("n2-standard-4",  4,  16.0,  0.1942),
    _InstanceSpec("n2-standard-8",  8,  32.0,  0.3884),
    _InstanceSpec("n2-standard-16",16,  64.0,  0.7768),
    _InstanceSpec("n2-standard-32",32, 128.0,  1.5536),
    _InstanceSpec("c2-standard-4",  4,  16.0,  0.2088),
    _InstanceSpec("c2-standard-8",  8,  32.0,  0.4176),
    _InstanceSpec("c2-standard-16",16,  64.0,  0.8352),
    _InstanceSpec("m2-ultramem-208", 208, 5888.0, 24.1726),
]

_AZURE_CATALOGUE: list[_InstanceSpec] = [
    _InstanceSpec("B1s",   1,   1.0,  0.0104),
    _InstanceSpec("B1ms",  1,   2.0,  0.0207),
    _InstanceSpec("B2s",   2,   4.0,  0.0416),
    _InstanceSpec("B2ms",  2,   8.0,  0.0832),
    _InstanceSpec("B4ms",  4,  16.0,  0.1664),
    _InstanceSpec("B8ms",  8,  32.0,  0.3328),
    _InstanceSpec("B16ms",16,  64.0,  0.6656),
    _InstanceSpec("D2s_v3", 2,   8.0,  0.0960),
    _InstanceSpec("D4s_v3", 4,  16.0,  0.1920),
    _InstanceSpec("D8s_v3", 8,  32.0,  0.3840),
    _InstanceSpec("D16s_v3",16,  64.0,  0.7680),
    _InstanceSpec("D32s_v3",32, 128.0,  1.5360),
    _InstanceSpec("F2s_v2", 2,   4.0,  0.0846),
    _InstanceSpec("F4s_v2", 4,   8.0,  0.1692),
    _InstanceSpec("F8s_v2", 8,  16.0,  0.3384),
    _InstanceSpec("E2s_v3", 2,  16.0,  0.1260),
    _InstanceSpec("E4s_v3", 4,  32.0,  0.2520),
    _InstanceSpec("E8s_v3", 8,  64.0,  0.5040),
]

# Storage pricing: USD per GB per month
_AWS_STORAGE_PRICE_PER_GB    = 0.08   # gp3
_GCP_STORAGE_PRICE_PER_GB    = 0.04   # pd-balanced
_AZURE_STORAGE_PRICE_PER_GB  = 0.0576 # Premium SSD LRS P4+

# Region name mappings for display
_AWS_REGIONS    = {"us": "us-east-1",    "eu": "eu-west-1",    "asia": "ap-southeast-1"}
_GCP_REGIONS    = {"us": "us-central1",  "eu": "europe-west1", "asia": "asia-east1"}
_AZURE_REGIONS  = {"us": "eastus",       "eu": "westeurope",   "asia": "southeastasia"}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CostCalculatorService:
    """
    Computes deterministic multi-cloud cost estimates from a workload spec.

    Usage:
        service = CostCalculatorService()
        estimates = service.compute(request)
    """

    def compute(self, request: CostEstimateRequest) -> list[ProviderEstimate]:
        """
        Return a ProviderEstimate for each requested provider.

        Args:
            request: The user's workload specification.

        Returns:
            List of ProviderEstimate objects (one per requested provider),
            sorted by total_monthly_usd ascending.
        """
        results: list[ProviderEstimate] = []

        if "aws" in request.providers:
            results.append(self._aws_estimate(request))
        if "gcp" in request.providers:
            results.append(self._gcp_estimate(request))
        if "azure" in request.providers:
            results.append(self._azure_estimate(request))

        # Sort cheapest-first for consistent UX
        results.sort(key=lambda e: e.total_monthly_usd)
        return results

    # ── Per-Provider Estimators ───────────────────────────────────────────

    def _aws_estimate(self, req: CostEstimateRequest) -> ProviderEstimate:
        instance = _select_instance(
            _AWS_CATALOGUE, req.cpu_cores, req.memory_gb
        )
        region = _AWS_REGIONS.get(req.region_preference, "us-east-1")
        compute_cost = round(instance.price_per_hour_usd * req.hours_per_month, 4)
        storage = _build_storage(
            "gp3",
            _AWS_STORAGE_PRICE_PER_GB,
            req.storage_gb,
        )
        return ProviderEstimate(
            provider="aws",
            provider_display="Amazon Web Services",
            region=region,
            instance=InstanceOption(
                instance_type=instance.instance_type,
                vcpus=instance.vcpus,
                memory_gb=instance.memory_gb,
                price_per_hour_usd=instance.price_per_hour_usd,
            ),
            compute_monthly_usd=compute_cost,
            storage=storage,
            total_monthly_usd=round(compute_cost + storage.total_cost_usd, 4),
            notes=[
                "On-demand pricing (no reserved instance discount applied)",
                f"Region: {region} (Linux AMI)",
                "Data transfer costs not included",
            ],
        )

    def _gcp_estimate(self, req: CostEstimateRequest) -> ProviderEstimate:
        instance = _select_instance(
            _GCP_CATALOGUE, req.cpu_cores, req.memory_gb
        )
        region = _GCP_REGIONS.get(req.region_preference, "us-central1")
        compute_cost = round(instance.price_per_hour_usd * req.hours_per_month, 4)
        storage = _build_storage(
            "pd-balanced",
            _GCP_STORAGE_PRICE_PER_GB,
            req.storage_gb,
        )
        return ProviderEstimate(
            provider="gcp",
            provider_display="Google Cloud Platform",
            region=region,
            instance=InstanceOption(
                instance_type=instance.instance_type,
                vcpus=instance.vcpus,
                memory_gb=instance.memory_gb,
                price_per_hour_usd=instance.price_per_hour_usd,
            ),
            compute_monthly_usd=compute_cost,
            storage=storage,
            total_monthly_usd=round(compute_cost + storage.total_cost_usd, 4),
            notes=[
                "On-demand pricing (no committed-use discount applied)",
                f"Region: {region}",
                "Sustained-use discount not applied (varies by actual uptime)",
            ],
        )

    def _azure_estimate(self, req: CostEstimateRequest) -> ProviderEstimate:
        instance = _select_instance(
            _AZURE_CATALOGUE, req.cpu_cores, req.memory_gb
        )
        region = _AZURE_REGIONS.get(req.region_preference, "eastus")
        compute_cost = round(instance.price_per_hour_usd * req.hours_per_month, 4)
        storage = _build_storage(
            "Premium SSD LRS",
            _AZURE_STORAGE_PRICE_PER_GB,
            req.storage_gb,
        )
        return ProviderEstimate(
            provider="azure",
            provider_display="Microsoft Azure",
            region=region,
            instance=InstanceOption(
                instance_type=instance.instance_type,
                vcpus=instance.vcpus,
                memory_gb=instance.memory_gb,
                price_per_hour_usd=instance.price_per_hour_usd,
            ),
            compute_monthly_usd=compute_cost,
            storage=storage,
            total_monthly_usd=round(compute_cost + storage.total_cost_usd, 4),
            notes=[
                "Pay-as-you-go pricing (no reserved instance discount applied)",
                f"Region: {region} (Linux VM)",
                "Azure Hybrid Benefit not applied",
            ],
        )


# ---------------------------------------------------------------------------
# Private Helpers
# ---------------------------------------------------------------------------


def _select_instance(
    catalogue: list[_InstanceSpec],
    min_vcpus: int,
    min_memory_gb: int,
) -> _InstanceSpec:
    """
    Pick the cheapest instance that satisfies both vCPU and memory requirements.

    Falls back to the largest instance if none match (should not happen for
    reasonable workload specs given our catalogue coverage).
    """
    eligible = [
        spec for spec in catalogue
        if spec.vcpus >= min_vcpus and spec.memory_gb >= min_memory_gb
    ]
    if eligible:
        return min(eligible, key=lambda s: s.price_per_hour_usd)
    # Fallback: largest in catalogue
    return max(catalogue, key=lambda s: s.memory_gb)


def _build_storage(
    storage_type: str,
    price_per_gb: float,
    storage_gb: int,
) -> StorageEstimate:
    """Build a StorageEstimate for the given storage class and capacity."""
    total = round(price_per_gb * storage_gb, 4)
    return StorageEstimate(
        storage_type=storage_type,
        price_per_gb_month_usd=price_per_gb,
        total_cost_usd=total,
    )
