"""
Infralytix — AWS Pricing Service Unit Tests.

Tests the real AWS Price List parser, dynamic URL construction,
filtering rules, smallest-instance matching (round-up), and 24-hour in-memory TTL caching.
All external I/O is mocked using the real AWS Price List fixture.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.pricing.aws_pricing_service import (
    AWSEC2InstancePrice,
    AWSPricingService,
    clear_cache,
    extract_ondemand_hourly_rate,
    is_standard_linux_ondemand,
    parse_memory_gb,
    parse_vcpu,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "aws_ec2_pricing_sample.json"


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    """Ensure in-memory cache is clean before and after every test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def sample_pricing_json() -> dict[str, Any]:
    """Load the sample AWS Price List JSON fixture."""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Helper Unit Tests
# ---------------------------------------------------------------------------


class TestParsingHelpers:
    """Test string parsing and attribute filtering helpers."""

    def test_parse_memory_gb_standard(self) -> None:
        assert parse_memory_gb("16 GiB") == 16.0
        assert parse_memory_gb("7.5 GiB") == 7.5
        assert parse_memory_gb("1,024 GiB") == 1024.0
        assert parse_memory_gb("0.5 GB") == 0.5

    def test_parse_memory_gb_edge_cases(self) -> None:
        assert parse_memory_gb(None) == 0.0
        assert parse_memory_gb("") == 0.0
        assert parse_memory_gb("not-a-number") == 0.0

    def test_parse_vcpu_standard(self) -> None:
        assert parse_vcpu("2") == 2
        assert parse_vcpu("4") == 4
        assert parse_vcpu("48") == 48

    def test_parse_vcpu_edge_cases(self) -> None:
        assert parse_vcpu(None) == 0
        assert parse_vcpu("") == 0
        assert parse_vcpu("abc") == 0

    def test_is_standard_linux_ondemand_filters(self) -> None:
        valid_attrs = {
            "operatingSystem": "Linux",
            "tenancy": "Shared",
            "preInstalledSw": "NA",
            "capacitystatus": "Used",
            "licenseModel": "No License required",
        }
        assert is_standard_linux_ondemand(valid_attrs) is True

        # Non-Linux
        assert is_standard_linux_ondemand({**valid_attrs, "operatingSystem": "Windows"}) is False
        assert is_standard_linux_ondemand({**valid_attrs, "operatingSystem": "RHEL"}) is False

        # Dedicated tenancy
        assert is_standard_linux_ondemand({**valid_attrs, "tenancy": "Dedicated"}) is False

        # Pre-installed SW
        assert is_standard_linux_ondemand({**valid_attrs, "preInstalledSw": "SQL Server"}) is False

        # Unused capacity reservation
        assert (
            is_standard_linux_ondemand(
                {**valid_attrs, "capacitystatus": "UnusedCapacityReservation"}
            )
            is False
        )

        # BYOL
        assert (
            is_standard_linux_ondemand({**valid_attrs, "licenseModel": "Bring your own license"})
            is False
        )

    def test_extract_ondemand_hourly_rate(self) -> None:
        terms = {
            "SKU123": {
                "SKU123.TERM1": {
                    "priceDimensions": {
                        "SKU123.TERM1.DIM1": {
                            "unit": "Hrs",
                            "pricePerUnit": {"USD": "0.1920000000"},
                        }
                    }
                }
            }
        }
        rate = extract_ondemand_hourly_rate("SKU123", terms)
        assert rate == 0.192

        # Non-existent SKU
        assert extract_ondemand_hourly_rate("MISSING", terms) is None


# ---------------------------------------------------------------------------
# URL & Parsing Tests
# ---------------------------------------------------------------------------


class TestAWSPricingServiceCore:
    """Test dynamic URL construction and fixture JSON parsing."""

    def test_dynamic_url_construction(self) -> None:
        service = AWSPricingService()
        url_us_east = service.get_pricing_url("us-east-1")
        assert (
            url_us_east
            == "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.json"
        )

        url_eu_west = service.get_pricing_url("eu-west-1")
        assert (
            url_eu_west
            == "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/eu-west-1/index.json"
        )

        # Regional aliases
        assert service.get_pricing_url("us") == url_us_east
        assert (
            service.get_pricing_url("eu")
            == "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/eu-west-1/index.json"
        )
        assert (
            service.get_pricing_url("asia")
            == "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/ap-southeast-1/index.json"
        )

    def test_parse_price_list_filters_correctly(self, sample_pricing_json: dict[str, Any]) -> None:
        service = AWSPricingService()
        instances = service.parse_price_list(sample_pricing_json, "us-east-1")

        types_found = {inst.instance_type for inst in instances}
        assert "t3.micro" in types_found
        assert "t3.medium" in types_found
        assert "t3.large" in types_found
        assert "m5.large" in types_found
        assert "m5.xlarge" in types_found
        assert "m5.2xlarge" in types_found
        assert "c5.xlarge" in types_found

        # Ignored SKUs (Windows, Dedicated, SQL, Unused capacity, BYOL) must not be in list
        skus_found = {inst.sku for inst in instances}
        assert "SKU-WINDOWS-IGNORED" not in skus_found
        assert "SKU-DEDICATED-IGNORED" not in skus_found
        assert "SKU-PREINSTALLED-IGNORED" not in skus_found
        assert "SKU-UNUSED-CAPACITY-IGNORED" not in skus_found
        assert "SKU-BYOL-IGNORED" not in skus_found

        # Verify exact rates
        micro = next(i for i in instances if i.instance_type == "t3.micro")
        assert micro.price_per_hour_usd == 0.0104
        assert micro.vcpus == 2
        assert micro.memory_gb == 1.0

        xlarge = next(i for i in instances if i.instance_type == "m5.xlarge")
        assert xlarge.price_per_hour_usd == 0.192
        assert xlarge.vcpus == 4
        assert xlarge.memory_gb == 16.0


# ---------------------------------------------------------------------------
# Instance Selection & Round-Up Tests
# ---------------------------------------------------------------------------


class TestInstanceSelection:
    """Test smallest instance selection matching vCPU and RAM (never undersizing)."""

    def test_select_instance_exact_match(self, sample_pricing_json: dict[str, Any]) -> None:
        service = AWSPricingService()
        instances = service.parse_price_list(sample_pricing_json, "us-east-1")

        # 2 vCPU, 4 GB -> t3.medium
        matched = service.select_instance(instances, min_vcpus=2, min_memory_gb=4.0)
        assert matched.instance_type == "t3.medium"

    def test_select_instance_rounds_up_never_undersizes(
        self, sample_pricing_json: dict[str, Any]
    ) -> None:
        service = AWSPricingService()
        instances = service.parse_price_list(sample_pricing_json, "us-east-1")

        # 3 vCPUs, 6 GB -> c5.xlarge (4 vCPUs, 8 GiB, $0.170)
        matched = service.select_instance(instances, min_vcpus=3, min_memory_gb=6.0)
        assert matched.instance_type == "c5.xlarge"
        assert matched.vcpus >= 3
        assert matched.memory_gb >= 6.0

        # 3 vCPUs, 12 GB -> m5.xlarge (4 vCPUs, 16 GiB, $0.192)
        matched2 = service.select_instance(instances, min_vcpus=3, min_memory_gb=12.0)
        assert matched2.instance_type == "m5.xlarge"
        assert matched2.vcpus >= 3
        assert matched2.memory_gb >= 12.0

    def test_select_instance_tie_breaker_cheapest(
        self, sample_pricing_json: dict[str, Any]
    ) -> None:
        service = AWSPricingService()
        instances = service.parse_price_list(sample_pricing_json, "us-east-1")

        # 2 vCPU, 8 GB: both t3.large ($0.0832) and m5.large ($0.0960) qualify.
        # t3.large should be chosen because it is cheaper.
        matched = service.select_instance(instances, min_vcpus=2, min_memory_gb=8.0)
        assert matched.instance_type == "t3.large"
        assert matched.price_per_hour_usd == 0.0832

    def test_fallback_when_exceeding_all_instances(self) -> None:
        service = AWSPricingService()
        instances = [
            AWSEC2InstancePrice("SKU1", "t3.small", 2, 2.0, 0.0208),
            AWSEC2InstancePrice("SKU2", "m5.large", 2, 8.0, 0.0960),
        ]
        # Request 64 vCPU, 256 GB RAM
        fallback = service.select_instance(instances, min_vcpus=64, min_memory_gb=256.0)
        assert fallback.instance_type == "m5.large"


# ---------------------------------------------------------------------------
# Mocked HTTP & In-Memory TTL Cache Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAWSPricingServiceAsync:
    """Test async API pricing fetching, calculations, and in-memory TTL caching."""

    async def test_get_instance_price_computation(
        self, sample_pricing_json: dict[str, Any]
    ) -> None:
        service = AWSPricingService()

        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_pricing_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        result = await service.get_instance_price(
            region_code="us-east-1",
            vcpus=4,
            memory_gb=16.0,
            hours_per_month=730.0,
            client=mock_client,
        )

        assert result.instance_type == "m5.xlarge"
        assert result.sku == "SKU-M5-XLARGE"
        assert result.vcpus == 4
        assert result.memory_gb == 16.0
        assert result.price_per_hour_usd == 0.192
        assert result.monthly_cost_low == round(0.192 * 730.0, 4)
        assert result.monthly_cost_high == round(0.192 * 730.0, 4)
        assert result.region_code == "us-east-1"
        assert mock_client.get.call_count == 1

    async def test_cache_hit_prevents_refetch_within_ttl(
        self, sample_pricing_json: dict[str, Any]
    ) -> None:
        service = AWSPricingService(cache_ttl=timedelta(hours=24))

        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_pricing_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        # First call: cache miss, triggers remote fetch
        res1 = await service.get_instance_price(
            region_code="us-east-1",
            vcpus=2,
            memory_gb=4.0,
            client=mock_client,
        )
        assert res1.instance_type == "t3.medium"
        assert mock_client.get.call_count == 1

        # Second call within TTL: cache hit, NO remote fetch
        res2 = await service.get_instance_price(
            region_code="us-east-1",
            vcpus=4,
            memory_gb=16.0,
            client=mock_client,
        )
        assert res2.instance_type == "m5.xlarge"
        assert mock_client.get.call_count == 1  # Still 1!

    async def test_cache_expiration_triggers_refetch(
        self, sample_pricing_json: dict[str, Any]
    ) -> None:
        service = AWSPricingService(cache_ttl=timedelta(hours=24))

        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_pricing_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        # Call at T0
        with patch("app.services.pricing.aws_pricing_service.datetime") as mock_dt:
            t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = t0

            await service.get_instance_price(
                region_code="us-east-1",
                vcpus=2,
                memory_gb=4.0,
                client=mock_client,
            )
            assert mock_client.get.call_count == 1

        # Call at T0 + 25 hours (TTL expired!)
        with patch("app.services.pricing.aws_pricing_service.datetime") as mock_dt:
            t_expired = t0 + timedelta(hours=25)
            mock_dt.now.return_value = t_expired

            await service.get_instance_price(
                region_code="us-east-1",
                vcpus=2,
                memory_gb=4.0,
                client=mock_client,
            )
            assert mock_client.get.call_count == 2  # Re-fetched!

    async def test_force_refresh_bypasses_cache(self, sample_pricing_json: dict[str, Any]) -> None:
        service = AWSPricingService(cache_ttl=timedelta(hours=24))

        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_pricing_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        # Initial fetch
        await service.fetch_price_list("us-east-1", client=mock_client)
        assert mock_client.get.call_count == 1

        # Force refresh
        await service.fetch_price_list("us-east-1", force_refresh=True, client=mock_client)
        assert mock_client.get.call_count == 2
