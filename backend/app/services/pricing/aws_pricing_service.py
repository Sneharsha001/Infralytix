"""
Infralytix — Real AWS Price List Service.

Fetches, parses, and caches official AWS EC2 Price List JSON files
(AWS Offer Index) directly from the AWS Pricing API.

Features:
  - Dynamic regional URL construction (AWS hosts all regional files on us-east-1 host).
  - In-memory caching per region_code with a 24-hour TTL (no Redis required).
  - Standard Linux On-Demand filtering (shared tenancy, standard capacity, no preinstalled SW).
  - Exact memory ('16 GiB') and vCPU attribute parsing.
  - Resource matching: selects smallest instance meeting or exceeding vCPU and RAM (round-up).
  - Deterministic pricing: monthly_cost_low and monthly_cost_high are set to the identical
    exact on-demand computed cost (hourly rate * hours_per_month), as AWS On-Demand rates
    are fixed per hour with no tiered billing variance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.logging.logging import get_logger
from app.services.pricing.region_mapping import resolve_aws_region

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants & Types
# ---------------------------------------------------------------------------

AWS_PRICING_BASE_HOST = "https://pricing.us-east-1.amazonaws.com"
DEFAULT_CACHE_TTL = timedelta(hours=24)
DEFAULT_AWS_STORAGE_PRICE_PER_GB = 0.08  # gp3 baseline ($/GB-month)


@dataclass(frozen=True)
class AWSEC2InstancePrice:
    """Parsed and validated EC2 instance pricing entry."""

    sku: str
    instance_type: str
    vcpus: int
    memory_gb: float
    price_per_hour_usd: float
    operating_system: str = "Linux"
    region_code: str = "us-east-1"


@dataclass(frozen=True)
class AWSEstimateResult:
    """
    Cost estimate result for a matched EC2 instance.

    Design Decision (v1 Scope):
      - EC2 Compute: Dynamically fetched and parsed from the official AWS Price List offer index.
      - EBS Storage: Dynamically parsing EBS volume pricing across complex IOPS/throughput
        dimensions from the offer file is explicitly out of scope for v1. AWS block storage
        is estimated using standard General Purpose SSD (gp3 baseline at $0.08/GB-month).
    """

    instance_type: str
    sku: str
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


# ---------------------------------------------------------------------------
# In-Memory Cache
# ---------------------------------------------------------------------------

# Keyed by region_code -> (fetched_at_utc, list[AWSEC2InstancePrice])
_CACHE: dict[str, tuple[datetime, list[AWSEC2InstancePrice]]] = {}


def clear_cache() -> None:
    """Clear the in-memory pricing cache (useful for testing)."""
    _CACHE.clear()
    logger.debug("aws_pricing_cache_cleared")


# ---------------------------------------------------------------------------
# Parsing Helpers
# ---------------------------------------------------------------------------


def parse_memory_gb(memory_str: str | None) -> float:
    """
    Parse AWS memory string into float GB.

    Examples:
      - '16 GiB' -> 16.0
      - '7.5 GiB' -> 7.5
      - '1,024 GiB' -> 1024.0
      - '0.5 GB' -> 0.5
    """
    if not memory_str:
        return 0.0
    cleaned = (
        memory_str.replace("GiB", "")
        .replace("GB", "")
        .replace(",", "")
        .strip()
    )
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        logger.warning(
            "aws_pricing_unparseable_memory",
            extra={"raw_value": memory_str},
        )
        return 0.0


def parse_vcpu(vcpu_str: str | None) -> int:
    """
    Parse AWS vcpu string into integer.

    Examples:
      - '2' -> 2
      - '48' -> 48
    """
    if not vcpu_str:
        return 0
    try:
        return int(vcpu_str)
    except (ValueError, TypeError):
        logger.warning(
            "aws_pricing_unparseable_vcpu",
            extra={"raw_value": vcpu_str},
        )
        return 0



def is_standard_linux_ondemand(attrs: dict[str, Any]) -> bool:
    """
    Filter to standard on-demand Linux instances.

    Filters out:
      - Windows / RHEL / SUSE / BYOL licenses
      - Dedicated host / Dedicated tenancy
      - Pre-installed software (SQL Server, etc.)
      - Unused capacity reservation variants
    """
    return (
        attrs.get("operatingSystem") == "Linux"
        and attrs.get("tenancy") == "Shared"
        and attrs.get("preInstalledSw") == "NA"
        and attrs.get("capacitystatus") == "Used"
        and attrs.get("licenseModel") == "No License required"
    )


def extract_ondemand_hourly_rate(
    sku: str,
    ondemand_terms: dict[str, Any],
) -> float | None:
    """
    Extract the hourly OnDemand USD rate for a given SKU.

    AWS structure:
      terms.OnDemand[sku] -> {
        term_id: {
          priceDimensions: {
            dimension_id: {
              pricePerUnit: {"USD": "0.1920000000"}
            }
          }
        }
      }
    """
    sku_terms = ondemand_terms.get(sku)
    if not isinstance(sku_terms, dict):
        return None

    for term in sku_terms.values():
        if not isinstance(term, dict):
            continue
        price_dimensions = term.get("priceDimensions", {})
        if not isinstance(price_dimensions, dict):
            continue
        for dim in price_dimensions.values():
            if not isinstance(dim, dict):
                continue
            price_per_unit = dim.get("pricePerUnit", {})
            if isinstance(price_per_unit, dict) and "USD" in price_per_unit:
                try:
                    price = float(price_per_unit["USD"])
                    if price > 0.0:
                        return price
                except (ValueError, TypeError):
                    continue
    return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AWSPricingService:
    """
    Service to fetch, parse, and evaluate AWS EC2 pricing from official Price List files.
    """

    def __init__(self, cache_ttl: timedelta = DEFAULT_CACHE_TTL) -> None:
        self.cache_ttl = cache_ttl

    @staticmethod
    def resolve_region_code(region_input: str) -> str:
        """Resolve region string or alias to canonical AWS region code."""
        return resolve_aws_region(region_input)


    def get_pricing_url(self, region_code: str) -> str:
        """
        Build the dynamic URL for the regional EC2 Price List file.

        The host is always pricing.us-east-1.amazonaws.com, while the path
        segment varies by region.
        """
        canonical_region = self.resolve_region_code(region_code)
        return (
            f"{AWS_PRICING_BASE_HOST}/offers/v1.0/aws/AmazonEC2/current/"
            f"{canonical_region}/index.json"
        )

    def parse_price_list(
        self,
        raw_data: dict[str, Any],
        region_code: str = "us-east-1",
    ) -> list[AWSEC2InstancePrice]:
        """
        Parse top-level products and terms.OnDemand into a list of AWSEC2InstancePrice.

        Filters strictly to standard shared Linux on-demand compute instances.
        """
        canonical_region = self.resolve_region_code(region_code)
        products: dict[str, Any] = raw_data.get("products", {})
        terms_ondemand: dict[str, Any] = (
            raw_data.get("terms", {}).get("OnDemand", {})
        )

        results: list[AWSEC2InstancePrice] = []

        for sku, product in products.items():
            if not isinstance(product, dict):
                continue

            attrs = product.get("attributes", {})
            if not isinstance(attrs, dict):
                continue

            if not is_standard_linux_ondemand(attrs):
                continue

            instance_type = attrs.get("instanceType")
            if not instance_type:
                continue

            vcpus = parse_vcpu(attrs.get("vcpu"))
            memory_gb = parse_memory_gb(attrs.get("memory"))
            if vcpus <= 0 or memory_gb <= 0.0:
                continue

            hourly_price = extract_ondemand_hourly_rate(sku, terms_ondemand)
            if hourly_price is None or hourly_price <= 0.0:
                continue

            results.append(
                AWSEC2InstancePrice(
                    sku=sku,
                    instance_type=str(instance_type),
                    vcpus=vcpus,
                    memory_gb=memory_gb,
                    price_per_hour_usd=hourly_price,
                    operating_system="Linux",
                    region_code=canonical_region,
                )
            )

        logger.info(
            "aws_pricing_parsed_successfully",
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
    ) -> list[AWSEC2InstancePrice]:
        """
        Retrieve parsed pricing data for region_code with 24-hour in-memory TTL caching.
        """
        canonical_region = self.resolve_region_code(region_code)
        now = datetime.now(UTC)

        if not force_refresh and canonical_region in _CACHE:
            cached_at, cached_data = _CACHE[canonical_region]
            if now - cached_at < self.cache_ttl:
                logger.debug(
                    "aws_pricing_cache_hit",
                    extra={
                        "region_code": canonical_region,
                        "cached_at": cached_at.isoformat(),
                    },
                )
                return cached_data

        url = self.get_pricing_url(canonical_region)
        logger.info(
            "aws_pricing_fetching_remote",
            extra={"url": url, "region": canonical_region},
        )

        if client is not None:
            response = await client.get(url)
            response.raise_for_status()
            raw_data = response.json()
        else:
            async with httpx.AsyncClient(timeout=60.0) as default_client:
                response = await default_client.get(url)
                response.raise_for_status()
                raw_data = response.json()

        parsed_instances = self.parse_price_list(raw_data, canonical_region)
        _CACHE[canonical_region] = (now, parsed_instances)
        return parsed_instances

    def select_instance(
        self,
        instances: list[AWSEC2InstancePrice],
        min_vcpus: int,
        min_memory_gb: float,
    ) -> AWSEC2InstancePrice:
        """
        Select the smallest instance meeting or exceeding min_vcpus and min_memory_gb.

        Never undersizes (rounds up). Sorts by (vcpus, memory_gb, price_per_hour_usd)
        to find the closest capacity match, tie-breaking by cheapest price.
        Falls back to the largest available instance if none meets both criteria.
        """
        if not instances:
            raise ValueError("No instances available in pricing catalogue")

        eligible = [
            inst
            for inst in instances
            if inst.vcpus >= min_vcpus and inst.memory_gb >= min_memory_gb
        ]

        if eligible:
            # Smallest instance that satisfies both requirements:
            # Primary: vcpus ascending, secondary: memory_gb ascending, tertiary: price ascending
            return min(
                eligible,
                key=lambda inst: (inst.vcpus, inst.memory_gb, inst.price_per_hour_usd),
            )

        # Fallback: largest instance in catalogue
        logger.warning(
            "aws_pricing_no_instance_met_requirements",
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
        storage_price_per_gb: float = DEFAULT_AWS_STORAGE_PRICE_PER_GB,
        client: httpx.AsyncClient | None = None,
    ) -> AWSEstimateResult:
        """
        Evaluate pricing for a workload requirement in the given AWS region.

        Decisions:
          - Low/High variance: monthly_cost_low and monthly_cost_high are set to the exact
            computed compute cost (hourly_rate * hours_per_month). Standard AWS On-Demand
            rates are fixed per-hour rates without tiered billing variance.
          - Storage scope: Dynamic EBS multi-tier volume parsing is out of scope for v1.
            AWS persistent block storage is estimated using standard General Purpose SSD
            (gp3 baseline at $0.08/GB-month).
        """
        canonical_region = self.resolve_region_code(region_code)
        instances = await self.fetch_price_list(canonical_region, client=client)
        selected = self.select_instance(instances, vcpus, memory_gb)

        compute_monthly = round(selected.price_per_hour_usd * hours_per_month, 4)
        storage_monthly = round(storage_gb * storage_price_per_gb, 4)
        total_monthly = round(compute_monthly + storage_monthly, 4)

        return AWSEstimateResult(
            instance_type=selected.instance_type,
            sku=selected.sku,
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
aws_pricing_service = AWSPricingService()

