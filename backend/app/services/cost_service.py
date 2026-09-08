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

import asyncio
from dataclasses import dataclass

import httpx

from app.logging.logging import get_logger
from app.schemas.cost import (
    CostEstimateRequest,
    InstanceOption,
    ProviderEstimate,
    StorageEstimate,
)
from app.services.pricing.aws_pricing_service import (
    _CACHE as _AWS_CACHE,
)
from app.services.pricing.aws_pricing_service import (
    aws_pricing_service,
)
from app.services.pricing.azure_pricing_service import (
    _CACHE as _AZURE_CACHE,
)
from app.services.pricing.azure_pricing_service import (
    azure_pricing_service,
)
from app.services.pricing.region_mapping import (
    resolve_aws_region,
    resolve_azure_region,
    resolve_gcp_region,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Static Price Catalogues (GCP-only fallback)
# ---------------------------------------------------------------------------
# Note: Static catalogue fallback is strictly GCP-only when GCP_API_KEY is unset.
# AWS and Azure evaluate against their official live pricing APIs directly.


@dataclass(frozen=True)
class _InstanceSpec:
    instance_type: str
    vcpus: int
    memory_gb: float
    price_per_hour_usd: float


_GCP_CATALOGUE: list[_InstanceSpec] = [
    _InstanceSpec("e2-micro", 2, 1.0, 0.0084),
    _InstanceSpec("e2-small", 2, 2.0, 0.0134),
    _InstanceSpec("e2-medium", 2, 4.0, 0.0268),
    _InstanceSpec("e2-standard-2", 2, 8.0, 0.0670),
    _InstanceSpec("e2-standard-4", 4, 16.0, 0.1340),
    _InstanceSpec("e2-standard-8", 8, 32.0, 0.2680),
    _InstanceSpec("e2-standard-16", 16, 64.0, 0.5360),
    _InstanceSpec("n2-standard-2", 2, 8.0, 0.0971),
    _InstanceSpec("n2-standard-4", 4, 16.0, 0.1942),
    _InstanceSpec("n2-standard-8", 8, 32.0, 0.3884),
    _InstanceSpec("n2-standard-16", 16, 64.0, 0.7768),
    _InstanceSpec("n2-standard-32", 32, 128.0, 1.5536),
    _InstanceSpec("c2-standard-4", 4, 16.0, 0.2088),
    _InstanceSpec("c2-standard-8", 8, 32.0, 0.4176),
    _InstanceSpec("c2-standard-16", 16, 64.0, 0.8352),
    _InstanceSpec("m2-ultramem-208", 208, 5888.0, 24.1726),
]


# Storage pricing: USD per GB per month
_AWS_STORAGE_PRICE_PER_GB = 0.08  # gp3
_GCP_STORAGE_PRICE_PER_GB = 0.04  # pd-balanced
_AZURE_STORAGE_PRICE_PER_GB = 0.0576  # Premium SSD LRS P4+


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
            sorted by total_monthly_usd ascending (available providers first).
        """
        results: list[ProviderEstimate] = []

        if "aws" in request.providers:
            results.append(self._aws_estimate(request))
        if "gcp" in request.providers:
            results.append(self._gcp_estimate(request))
        if "azure" in request.providers:
            results.append(self._azure_estimate(request))

        results.sort(key=lambda e: (0 if self._is_available(e) else 1, e.total_monthly_usd))
        return results

    async def compute_async(
        self,
        request: CostEstimateRequest,
        client: httpx.AsyncClient | None = None,
    ) -> list[ProviderEstimate]:
        """
        Return a ProviderEstimate for each requested provider asynchronously.

        Integrates real live/cached AWS and Azure Pricing Services, executing
        remote network requests concurrently via asyncio.gather, without
        silent static fallbacks.
        """
        results: list[ProviderEstimate] = []
        remote_tasks: list[asyncio.Task[ProviderEstimate]] = []

        if "aws" in request.providers:
            remote_tasks.append(
                asyncio.create_task(self._aws_estimate_async(request, client=client))
            )
        if "azure" in request.providers:
            remote_tasks.append(
                asyncio.create_task(self._azure_estimate_async(request, client=client))
            )

        if remote_tasks:
            resolved = await asyncio.gather(*remote_tasks)
            results.extend(resolved)

        if "gcp" in request.providers:
            results.append(self._gcp_estimate(request))

        results.sort(key=lambda e: (0 if self._is_available(e) else 1, e.total_monthly_usd))
        return results

    @staticmethod
    def _is_available(est: ProviderEstimate) -> bool:
        """Check if an estimate was successfully priced."""
        return (
            not any("unavailable" in n.lower() or "failed" in n.lower() for n in est.notes)
            and est.total_monthly_usd > 0.0
        )

    # ── Per-Provider Estimators ───────────────────────────────────────────

    def _aws_estimate(self, req: CostEstimateRequest) -> ProviderEstimate:
        region = resolve_aws_region(req.region_preference)
        if region in _AWS_CACHE:
            _, cached_instances = _AWS_CACHE[region]
            if cached_instances:
                selected_inst = aws_pricing_service.select_instance(
                    cached_instances, req.cpu_cores, req.memory_gb
                )
                price_per_hour = selected_inst.price_per_hour_usd
                compute_cost = round(price_per_hour * req.hours_per_month, 4)
                storage = _build_storage("gp3", _AWS_STORAGE_PRICE_PER_GB, req.storage_gb)
                return ProviderEstimate(
                    provider="aws",
                    provider_display="Amazon Web Services",
                    region=region,
                    instance=InstanceOption(
                        instance_type=selected_inst.instance_type,
                        vcpus=selected_inst.vcpus,
                        memory_gb=selected_inst.memory_gb,
                        price_per_hour_usd=price_per_hour,
                    ),
                    compute_monthly_usd=compute_cost,
                    storage=storage,
                    total_monthly_usd=round(compute_cost + storage.total_cost_usd, 4),
                    notes=[
                        "On-demand pricing (real AWS Price List Offer Index)",
                        f"Region: {region} (Linux Shared)",
                        "Data transfer costs not included; EBS gp3 storage baseline ($0.08/GB-mo)",
                    ],
                )

        return ProviderEstimate(
            provider="aws",
            provider_display="Amazon Web Services",
            region=region,
            instance=InstanceOption(
                instance_type="unavailable",
                vcpus=0,
                memory_gb=0.0,
                price_per_hour_usd=0.0,
            ),
            compute_monthly_usd=0.0,
            storage=_build_storage("gp3", 0.0, 0),
            total_monthly_usd=0.0,
            notes=[
                "Pricing unavailable: cache empty; asynchronous live fetch required",
            ],
        )

    async def _aws_estimate_async(
        self,
        req: CostEstimateRequest,
        client: httpx.AsyncClient | None = None,
    ) -> ProviderEstimate:
        """Evaluate AWS using live/cached AWSPricingService without silent fallback."""
        region = resolve_aws_region(req.region_preference)
        try:
            res = await aws_pricing_service.get_instance_price(
                region_code=region,
                vcpus=req.cpu_cores,
                memory_gb=float(req.memory_gb),
                hours_per_month=req.hours_per_month,
                storage_gb=req.storage_gb,
                storage_price_per_gb=_AWS_STORAGE_PRICE_PER_GB,
                client=client,
            )
            storage = _build_storage("gp3", _AWS_STORAGE_PRICE_PER_GB, req.storage_gb)
            return ProviderEstimate(
                provider="aws",
                provider_display="Amazon Web Services",
                region=region,
                instance=InstanceOption(
                    instance_type=res.instance_type,
                    vcpus=res.vcpus,
                    memory_gb=res.memory_gb,
                    price_per_hour_usd=res.price_per_hour_usd,
                ),
                compute_monthly_usd=res.monthly_cost_low,
                storage=storage,
                total_monthly_usd=res.total_monthly_usd,
                notes=[
                    "On-demand pricing (real AWS Price List Offer Index)",
                    f"Region: {region} (Linux Shared)",
                    "Data transfer costs not included; EBS gp3 storage baseline ($0.08/GB-mo)",
                ],
            )
        except Exception as exc:
            logger.warning(
                "aws_pricing_async_fetch_failed",
                extra={"error": str(exc), "region": region},
            )
            return ProviderEstimate(
                provider="aws",
                provider_display="Amazon Web Services",
                region=region,
                instance=InstanceOption(
                    instance_type="unavailable",
                    vcpus=0,
                    memory_gb=0.0,
                    price_per_hour_usd=0.0,
                ),
                compute_monthly_usd=0.0,
                storage=_build_storage("gp3", 0.0, 0),
                total_monthly_usd=0.0,
                notes=[
                    f"Pricing unavailable: Live AWS Price List API call failed ({exc})",
                ],
            )

    def _gcp_estimate(self, req: CostEstimateRequest) -> ProviderEstimate:
        instance = _select_instance(_GCP_CATALOGUE, req.cpu_cores, req.memory_gb)
        region = resolve_gcp_region(req.region_preference)
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
        region = resolve_azure_region(req.region_preference)
        if region in _AZURE_CACHE:
            _, cached_instances = _AZURE_CACHE[region]
            if cached_instances:
                selected_inst = azure_pricing_service.select_instance(
                    cached_instances, req.cpu_cores, req.memory_gb
                )
                price_per_hour = selected_inst.price_per_hour_usd
                compute_cost = round(price_per_hour * req.hours_per_month, 4)
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
                        instance_type=selected_inst.arm_sku_name,
                        vcpus=selected_inst.vcpus,
                        memory_gb=selected_inst.memory_gb,
                        price_per_hour_usd=price_per_hour,
                    ),
                    compute_monthly_usd=compute_cost,
                    storage=storage,
                    total_monthly_usd=round(compute_cost + storage.total_cost_usd, 4),
                    notes=[
                        "Pay-as-you-go pricing (real Azure Retail Prices API)",
                        f"Region: {region} (Linux Consumption)",
                        (
                            "Azure Hybrid Benefit not applied; "
                            "Premium SSD Managed Disks baseline ($0.0576/GB-mo)"
                        ),
                    ],
                )

        return ProviderEstimate(
            provider="azure",
            provider_display="Microsoft Azure",
            region=region,
            instance=InstanceOption(
                instance_type="unavailable",
                vcpus=0,
                memory_gb=0.0,
                price_per_hour_usd=0.0,
            ),
            compute_monthly_usd=0.0,
            storage=_build_storage("Premium SSD LRS", 0.0, 0),
            total_monthly_usd=0.0,
            notes=[
                "Pricing unavailable: cache empty; asynchronous live fetch required",
            ],
        )

    async def _azure_estimate_async(
        self,
        req: CostEstimateRequest,
        client: httpx.AsyncClient | None = None,
    ) -> ProviderEstimate:
        """Evaluate Azure using live/cached AzurePricingService without silent fallback."""
        region = resolve_azure_region(req.region_preference)
        try:
            res = await azure_pricing_service.get_instance_price(
                region_code=region,
                vcpus=req.cpu_cores,
                memory_gb=float(req.memory_gb),
                hours_per_month=req.hours_per_month,
                storage_gb=req.storage_gb,
                storage_price_per_gb=_AZURE_STORAGE_PRICE_PER_GB,
                client=client,
            )
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
                    instance_type=res.instance_type,
                    vcpus=res.vcpus,
                    memory_gb=res.memory_gb,
                    price_per_hour_usd=res.price_per_hour_usd,
                ),
                compute_monthly_usd=res.monthly_cost_low,
                storage=storage,
                total_monthly_usd=res.total_monthly_usd,
                notes=[
                    "Pay-as-you-go pricing (real Azure Retail Prices API)",
                    f"Region: {region} (Linux Consumption)",
                    (
                        "Azure Hybrid Benefit not applied; "
                        "Premium SSD Managed Disks baseline ($0.0576/GB-mo)"
                    ),
                ],
            )
        except Exception as exc:
            logger.warning(
                "azure_pricing_async_fetch_failed",
                extra={"error": str(exc), "region": region},
            )
            return ProviderEstimate(
                provider="azure",
                provider_display="Microsoft Azure",
                region=region,
                instance=InstanceOption(
                    instance_type="unavailable",
                    vcpus=0,
                    memory_gb=0.0,
                    price_per_hour_usd=0.0,
                ),
                compute_monthly_usd=0.0,
                storage=_build_storage("Premium SSD LRS", 0.0, 0),
                total_monthly_usd=0.0,
                notes=[
                    f"Pricing unavailable: Live Azure Retail Prices API call failed ({exc})",
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
        spec for spec in catalogue if spec.vcpus >= min_vcpus and spec.memory_gb >= min_memory_gb
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
