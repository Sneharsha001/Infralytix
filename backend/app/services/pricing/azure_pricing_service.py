"""
Infralytix — Real Azure Retail Prices Service.

Fetches, parses, and caches official Azure VM Retail Prices
directly from the Microsoft Azure Retail Prices API.

Features:
  - Dynamic OData query construction using canonical armRegionName.
  - In-memory caching per region_code with a 24-hour TTL (no Redis required).
  - Standard Linux On-Demand consumption filtering
    (excludes Windows, Spot, Low Priority, Dedicated Hosts).
  - Spec extraction via known Azure SKU catalogue and family regex parsing.
  - Resource matching: selects smallest instance meeting or exceeding vCPU and RAM (round-up).
  - Storage estimation: Premium SSD Managed Disks baseline ($0.0576/GB-month).
  - Deterministic pricing: monthly_cost_low and monthly_cost_high set to identical
    on-demand computed cost (hourly rate * 730 hours/month).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.logging.logging import get_logger
from app.services.pricing.region_mapping import resolve_azure_region

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants & Types
# ---------------------------------------------------------------------------

AZURE_RETAIL_PRICES_API_URL = "https://prices.azure.com/api/retail/prices"
DEFAULT_CACHE_TTL = timedelta(hours=24)
DEFAULT_AZURE_STORAGE_PRICE_PER_GB = 0.0576  # Premium SSD Managed Disk LRS baseline ($/GB-month)
DEFAULT_MAX_PAGES = 5

# Well-known Azure VM specifications: (vCPUs, RAM in GB)
KNOWN_AZURE_VM_SPECS: dict[str, tuple[int, float]] = {
    # Burstable (B-series)
    "Standard_B1s": (1, 1.0),
    "Standard_B1ms": (1, 2.0),
    "Standard_B2s": (2, 4.0),
    "Standard_B2ms": (2, 8.0),
    "Standard_B4ms": (4, 16.0),
    "Standard_B8ms": (8, 32.0),
    "Standard_B12ms": (12, 48.0),
    "Standard_B16ms": (16, 64.0),
    "Standard_B20ms": (20, 80.0),
    # D-series (General Purpose - 4GB RAM per vCPU)
    "Standard_D2s_v3": (2, 8.0),
    "Standard_D4s_v3": (4, 16.0),
    "Standard_D8s_v3": (8, 32.0),
    "Standard_D16s_v3": (16, 64.0),
    "Standard_D32s_v3": (32, 128.0),
    "Standard_D64s_v3": (64, 256.0),
    "Standard_D2s_v4": (2, 8.0),
    "Standard_D4s_v4": (4, 16.0),
    "Standard_D8s_v4": (8, 32.0),
    "Standard_D16s_v4": (16, 64.0),
    "Standard_D32s_v4": (32, 128.0),
    "Standard_D2s_v5": (2, 8.0),
    "Standard_D4s_v5": (4, 16.0),
    "Standard_D8s_v5": (8, 32.0),
    "Standard_D16s_v5": (16, 64.0),
    "Standard_D32s_v5": (32, 128.0),
    "Standard_D64s_v5": (64, 256.0),
    "Standard_D2as_v5": (2, 8.0),
    "Standard_D4as_v5": (4, 16.0),
    "Standard_D8as_v5": (8, 32.0),
    # E-series (Memory Optimized - 8GB RAM per vCPU)
    "Standard_E2s_v3": (2, 16.0),
    "Standard_E4s_v3": (4, 32.0),
    "Standard_E8s_v3": (8, 64.0),
    "Standard_E16s_v3": (16, 128.0),
    "Standard_E2s_v5": (2, 16.0),
    "Standard_E4s_v5": (4, 32.0),
    "Standard_E8s_v5": (8, 64.0),
    "Standard_E16s_v5": (16, 128.0),
    "Standard_E32s_v5": (32, 256.0),
    # F-series (Compute Optimized - 2GB RAM per vCPU)
    "Standard_F2s_v2": (2, 4.0),
    "Standard_F4s_v2": (4, 8.0),
    "Standard_F8s_v2": (8, 16.0),
    "Standard_F16s_v2": (16, 32.0),
    "Standard_F32s_v2": (32, 64.0),
}


@dataclass(frozen=True)
class AzureVMInstancePrice:
    """Parsed and validated Azure VM instance pricing entry."""

    arm_sku_name: str
    sku_name: str
    meter_name: str
    product_name: str
    vcpus: int
    memory_gb: float
    price_per_hour_usd: float
    region_code: str = "eastus"
    operating_system: str = "Linux"


@dataclass(frozen=True)
class AzureEstimateResult:
    """
    Cost estimate result for a matched Azure VM instance.

    Design Decision (v1 Scope):
      - Azure Compute: Dynamically fetched and parsed from Azure Retail Prices API.
      - Azure Storage: Premium SSD Managed Disks baseline ($0.0576/GB-month).
    """

    instance_type: str
    arm_sku_name: str
    vcpus: int
    memory_gb: float
    price_per_hour_usd: float
    hours_per_month: float
    monthly_cost_low: float
    monthly_cost_high: float
    region_code: str
    storage_gb: int = 0
    storage_monthly_usd: float = 0.0
    total_monthly_usd: float = 0.0


# Fallback catalogue used when network is offline and cache is empty
FALLBACK_AZURE_INSTANCES: list[AzureVMInstancePrice] = [
    AzureVMInstancePrice(
        arm_sku_name="Standard_B1s",
        sku_name="B1s",
        meter_name="B1s",
        product_name="Virtual Machines BS Series",
        vcpus=1,
        memory_gb=1.0,
        price_per_hour_usd=0.0104,
        region_code="eastus",
    ),
    AzureVMInstancePrice(
        arm_sku_name="Standard_B2s",
        sku_name="B2s",
        meter_name="B2s",
        product_name="Virtual Machines BS Series",
        vcpus=2,
        memory_gb=4.0,
        price_per_hour_usd=0.0416,
        region_code="eastus",
    ),
    AzureVMInstancePrice(
        arm_sku_name="Standard_D2s_v3",
        sku_name="D2s v3",
        meter_name="D2s v3",
        product_name="Virtual Machines Dsv3 Series",
        vcpus=2,
        memory_gb=8.0,
        price_per_hour_usd=0.096,
        region_code="eastus",
    ),
    AzureVMInstancePrice(
        arm_sku_name="Standard_D4s_v5",
        sku_name="D4s v5",
        meter_name="D4s v5",
        product_name="Virtual Machines Dsv5 Series",
        vcpus=4,
        memory_gb=16.0,
        price_per_hour_usd=0.192,
        region_code="eastus",
    ),
    AzureVMInstancePrice(
        arm_sku_name="Standard_D8s_v5",
        sku_name="D8s v5",
        meter_name="D8s v5",
        product_name="Virtual Machines Dsv5 Series",
        vcpus=8,
        memory_gb=32.0,
        price_per_hour_usd=0.384,
        region_code="eastus",
    ),
    AzureVMInstancePrice(
        arm_sku_name="Standard_E2s_v5",
        sku_name="E2s v5",
        meter_name="E2s v5",
        product_name="Virtual Machines Esv5 Series",
        vcpus=2,
        memory_gb=16.0,
        price_per_hour_usd=0.126,
        region_code="eastus",
    ),
    AzureVMInstancePrice(
        arm_sku_name="Standard_F2s_v2",
        sku_name="F2s v2",
        meter_name="F2s v2",
        product_name="Virtual Machines FSv2 Series",
        vcpus=2,
        memory_gb=4.0,
        price_per_hour_usd=0.085,
        region_code="eastus",
    ),
]


# ---------------------------------------------------------------------------
# In-Memory Cache
# ---------------------------------------------------------------------------

# Keyed by region_code -> (fetched_at_utc, list[AzureVMInstancePrice])
_CACHE: dict[str, tuple[datetime, list[AzureVMInstancePrice]]] = {}


def clear_cache() -> None:
    """Clear the in-memory pricing cache (useful for testing)."""
    _CACHE.clear()
    logger.debug("azure_pricing_cache_cleared")


# ---------------------------------------------------------------------------
# Parsing Helpers
# ---------------------------------------------------------------------------


def normalize_sku_name(arm_sku_name: str | None, sku_name: str | None) -> str:
    """
    Produce a canonical Azure SKU name (e.g. 'Standard_D2s_v3').
    """
    if arm_sku_name and arm_sku_name.strip():
        name = arm_sku_name.strip()
        return name if name.startswith("Standard_") else f"Standard_{name}"
    if sku_name and sku_name.strip():
        name = sku_name.strip().replace(" ", "_")
        return name if name.startswith("Standard_") else f"Standard_{name}"
    return ""


def parse_azure_sku_spec(sku_name: str) -> tuple[int, float] | None:
    """
    Determine (vCPUs, RAM_GB) from an Azure VM SKU name.

    First queries the KNOWN_AZURE_VM_SPECS dictionary. If not found, applies
    naming convention heuristics for standard Azure families:
      - Standard_D{n}* -> n vCPUs, n * 4 GB RAM
      - Standard_E{n}* -> n vCPUs, n * 8 GB RAM
      - Standard_F{n}* -> n vCPUs, n * 2 GB RAM
      - Standard_B{n}ms -> n vCPUs, n * 4 GB RAM
      - Standard_B{n}s -> n vCPUs, n * 2 GB RAM
    """
    norm = sku_name.strip()
    if not norm.startswith("Standard_"):
        norm = f"Standard_{norm}"

    # 1. Exact lookup
    if norm in KNOWN_AZURE_VM_SPECS:
        return KNOWN_AZURE_VM_SPECS[norm]

    # 2. Heuristic parsing for D-series (4 GB per vCPU)
    match_d = re.match(r"^Standard_D(\d+)", norm)
    if match_d:
        vcpus = int(match_d.group(1))
        return (vcpus, float(vcpus * 4))

    # 3. Heuristic parsing for E-series (8 GB per vCPU)
    match_e = re.match(r"^Standard_E(\d+)", norm)
    if match_e:
        vcpus = int(match_e.group(1))
        return (vcpus, float(vcpus * 8))

    # 4. Heuristic parsing for F-series (2 GB per vCPU)
    match_f = re.match(r"^Standard_F(\d+)", norm)
    if match_f:
        vcpus = int(match_f.group(1))
        return (vcpus, float(vcpus * 2))

    # 5. Heuristic parsing for B-series
    match_bms = re.match(r"^Standard_B(\d+)ms", norm)
    if match_bms:
        vcpus = int(match_bms.group(1))
        return (vcpus, float(vcpus * 4))

    match_bs = re.match(r"^Standard_B(\d+)s", norm)
    if match_bs:
        vcpus = int(match_bs.group(1))
        return (vcpus, float(vcpus * 2))

    return None


def is_standard_linux_ondemand(item: dict[str, Any]) -> bool:
    """
    Filter raw Azure Retail Prices API item to standard Linux On-Demand VMs.

    Filters out:
      - Non-Virtual Machines services
      - Non-Consumption price types (Reservations, Savings Plans)
      - Non-Hourly billing units
      - Windows licenses / products
      - Spot and Low Priority pricing
      - Dedicated host instances
      - Zero or negative pricing
    """
    if item.get("serviceName") != "Virtual Machines":
        return False
    if item.get("type") != "Consumption":
        return False
    if item.get("unitOfMeasure") != "1 Hour":
        return False

    product_name = str(item.get("productName") or "").lower()
    sku_name = str(item.get("skuName") or "").lower()
    meter_name = str(item.get("meterName") or "").lower()

    # Exclude Windows
    if "windows" in product_name or "windows" in sku_name or "windows" in meter_name:
        return False

    # Exclude Spot and Low Priority
    if "spot" in sku_name or "spot" in meter_name:
        return False
    if "low priority" in sku_name or "low priority" in meter_name:
        return False

    # Exclude Dedicated Hosts
    if "dedicated" in product_name or "dedicated" in sku_name:
        return False

    retail_price = item.get("retailPrice")
    if retail_price is None:
        return False
    try:
        return float(retail_price) > 0.0
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AzurePricingService:
    """
    Service to fetch, parse, and evaluate Azure Virtual Machine pricing
    from the official Azure Retail Prices API.
    """

    def __init__(self, cache_ttl: timedelta = DEFAULT_CACHE_TTL) -> None:
        self.cache_ttl = cache_ttl

    @staticmethod
    def resolve_region_code(region_input: str) -> str:
        """Resolve region string or alias to canonical Azure armRegionName."""
        return resolve_azure_region(region_input)

    def get_pricing_url(self, region_code: str) -> str:
        """
        Build the initial query URL for the Azure Retail Prices API.
        """
        canonical_region = self.resolve_region_code(region_code)
        odata_filter = (
            f"serviceName eq 'Virtual Machines' and "
            f"armRegionName eq '{canonical_region}' and "
            f"priceType eq 'Consumption'"
        )
        return f"{AZURE_RETAIL_PRICES_API_URL}?$filter={odata_filter}"

    def parse_price_list(
        self,
        raw_items: list[dict[str, Any]],
        region_code: str = "eastus",
    ) -> list[AzureVMInstancePrice]:
        """
        Parse raw Azure API items into a list of AzureVMInstancePrice.
        Filters strictly to standard Linux on-demand compute instances.
        """
        canonical_region = self.resolve_region_code(region_code)
        results: list[AzureVMInstancePrice] = []
        seen_skus: set[str] = set()

        for item in raw_items:
            if not is_standard_linux_ondemand(item):
                continue

            arm_sku = item.get("armSkuName")
            sku = item.get("skuName")
            normalized_name = normalize_sku_name(arm_sku, sku)
            if not normalized_name or normalized_name in seen_skus:
                continue

            specs = parse_azure_sku_spec(normalized_name)
            if specs is None:
                continue

            vcpus, memory_gb = specs
            if vcpus <= 0 or memory_gb <= 0.0:
                continue

            price = float(item["retailPrice"])
            seen_skus.add(normalized_name)
            results.append(
                AzureVMInstancePrice(
                    arm_sku_name=normalized_name,
                    sku_name=str(sku or normalized_name),
                    meter_name=str(item.get("meterName") or ""),
                    product_name=str(item.get("productName") or ""),
                    vcpus=vcpus,
                    memory_gb=memory_gb,
                    price_per_hour_usd=price,
                    region_code=canonical_region,
                    operating_system="Linux",
                )
            )

        logger.info(
            "azure_pricing_parsed_successfully",
            extra={
                "region_code": canonical_region,
                "instance_count": len(results),
            },
        )
        return results

    async def fetch_price_list(
        self,
        region_code: str,
        force_refresh: bool = False,
        client: httpx.AsyncClient | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> list[AzureVMInstancePrice]:
        """
        Retrieve parsed Azure pricing data for region_code with 24-hour TTL caching.
        Paginates up to max_pages using NextPageLink.
        """
        canonical_region = self.resolve_region_code(region_code)
        now = datetime.now(UTC)

        if not force_refresh and canonical_region in _CACHE:
            cached_at, cached_data = _CACHE[canonical_region]
            if now - cached_at < self.cache_ttl:
                logger.debug(
                    "azure_pricing_cache_hit",
                    extra={
                        "region_code": canonical_region,
                        "cached_at": cached_at.isoformat(),
                    },
                )
                return cached_data

        url: str | None = self.get_pricing_url(canonical_region)
        logger.info(
            "azure_pricing_fetching_remote",
            extra={"url": url, "region": canonical_region},
        )

        all_items: list[dict[str, Any]] = []
        page_count = 0

        try:
            if client is not None:
                while url and page_count < max_pages:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    all_items.extend(data.get("Items", []))
                    url = data.get("NextPageLink")
                    page_count += 1
            else:
                async with httpx.AsyncClient(timeout=30.0) as default_client:
                    while url and page_count < max_pages:
                        resp = await default_client.get(url)
                        resp.raise_for_status()
                        data = resp.json()
                        all_items.extend(data.get("Items", []))
                        url = data.get("NextPageLink")
                        page_count += 1

            parsed_instances = self.parse_price_list(all_items, canonical_region)
            if parsed_instances:
                _CACHE[canonical_region] = (now, parsed_instances)
                return parsed_instances

        except Exception as exc:
            logger.error(
                "azure_pricing_fetch_failed",
                extra={"region_code": canonical_region, "error": str(exc)},
            )
            # If cache has any stale data, return it
            if canonical_region in _CACHE:
                return _CACHE[canonical_region][1]

        # Fallback catalogue when remote call fails and cache is empty
        logger.warning(
            "azure_pricing_using_fallback_catalogue",
            extra={"region_code": canonical_region},
        )
        return list(FALLBACK_AZURE_INSTANCES)

    def select_instance(
        self,
        instances: list[AzureVMInstancePrice],
        min_vcpus: int,
        min_memory_gb: float,
    ) -> AzureVMInstancePrice:
        """
        Select the smallest instance meeting or exceeding min_vcpus and min_memory_gb.

        Never undersizes (rounds up). Sorts by (vcpus, memory_gb, price_per_hour_usd)
        to find the closest capacity match, tie-breaking by cheapest price.
        Falls back to the largest available instance if none meets both criteria.
        """
        if not instances:
            raise ValueError("No instances available in Azure pricing catalogue")

        eligible = [
            inst
            for inst in instances
            if inst.vcpus >= min_vcpus and inst.memory_gb >= min_memory_gb
        ]

        if eligible:
            return min(
                eligible,
                key=lambda inst: (inst.vcpus, inst.memory_gb, inst.price_per_hour_usd),
            )

        logger.warning(
            "azure_pricing_no_instance_met_requirements",
            extra={
                "min_vcpus": min_vcpus,
                "min_memory_gb": min_memory_gb,
            },
        )
        return max(instances, key=lambda inst: (inst.vcpus, inst.memory_gb))

    async def get_instance_price(
        self,
        region_code: str,
        vcpus: int,
        memory_gb: float,
        hours_per_month: float = 730.0,
        storage_gb: int = 0,
        storage_price_per_gb: float = DEFAULT_AZURE_STORAGE_PRICE_PER_GB,
        client: httpx.AsyncClient | None = None,
    ) -> AzureEstimateResult:
        """
        Evaluate pricing for a workload requirement in the given Azure region.

        Decisions:
          - Low/High variance: monthly_cost_low and monthly_cost_high are set to the exact
            computed compute cost (hourly_rate * hours_per_month). Standard Azure Consumption
            rates are fixed per-hour rates without tiered billing variance.
          - Storage scope: Premium SSD Managed Disks baseline ($0.0576/GB-month).
        """
        canonical_region = self.resolve_region_code(region_code)
        instances = await self.fetch_price_list(canonical_region, client=client)
        selected = self.select_instance(instances, vcpus, memory_gb)

        compute_monthly = round(selected.price_per_hour_usd * hours_per_month, 4)
        storage_monthly = round(storage_gb * storage_price_per_gb, 4)
        total_monthly = round(compute_monthly + storage_monthly, 4)

        return AzureEstimateResult(
            instance_type=selected.arm_sku_name,
            arm_sku_name=selected.arm_sku_name,
            vcpus=selected.vcpus,
            memory_gb=selected.memory_gb,
            price_per_hour_usd=selected.price_per_hour_usd,
            hours_per_month=hours_per_month,
            monthly_cost_low=compute_monthly,
            monthly_cost_high=compute_monthly,
            region_code=canonical_region,
            storage_gb=storage_gb,
            storage_monthly_usd=storage_monthly,
            total_monthly_usd=total_monthly,
        )


# Singleton instance
azure_pricing_service = AzurePricingService()
