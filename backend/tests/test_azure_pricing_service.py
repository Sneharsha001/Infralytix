"""
Infralytix — Azure Pricing Service Unit Tests.

Tests the Azure Retail Prices API parser, OData query construction,
filtering rules (Linux consumption only; excludes Windows, Spot, Low Priority, Dedicated),
spec parsing, smallest-instance matching (round-up), and 24-hour in-memory TTL caching.
All external I/O is mocked using the real Azure Retail Prices API fixture.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.pricing.azure_pricing_service import (
    AzurePricingService,
    AzureVMInstancePrice,
    clear_cache,
    is_standard_linux_ondemand,
    normalize_sku_name,
    parse_azure_sku_spec,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "azure_vm_pricing_sample.json"


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    """Ensure in-memory cache is clean before and after every test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def sample_pricing_json() -> dict[str, Any]:
    """Load the sample Azure Retail Prices JSON fixture."""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Helper Unit Tests
# ---------------------------------------------------------------------------


class TestAzureParsingHelpers:
    """Test SKU normalization, spec parsing, and item filtering helpers."""

    def test_normalize_sku_name(self) -> None:
        assert normalize_sku_name("Standard_D2s_v3", "D2s v3") == "Standard_D2s_v3"
        assert normalize_sku_name(None, "D2s v3") == "Standard_D2s_v3"
        assert normalize_sku_name("", "B1s") == "Standard_B1s"
        assert normalize_sku_name("Standard_B1s", None) == "Standard_B1s"
        assert normalize_sku_name(None, None) == ""

    def test_parse_azure_sku_spec_known(self) -> None:
        assert parse_azure_sku_spec("Standard_B1s") == (1, 1.0)
        assert parse_azure_sku_spec("Standard_B2s") == (2, 4.0)
        assert parse_azure_sku_spec("Standard_D2s_v3") == (2, 8.0)
        assert parse_azure_sku_spec("Standard_D4s_v5") == (4, 16.0)
        assert parse_azure_sku_spec("Standard_E2s_v5") == (2, 16.0)
        assert parse_azure_sku_spec("Standard_F2s_v2") == (2, 4.0)

    def test_parse_azure_sku_spec_without_prefix(self) -> None:
        assert parse_azure_sku_spec("B1s") == (1, 1.0)
        assert parse_azure_sku_spec("D4s_v5") == (4, 16.0)

    def test_parse_azure_sku_spec_heuristics(self) -> None:
        # D-series (4 GB per vCPU)
        assert parse_azure_sku_spec("Standard_D12_v2") == (12, 48.0)
        # E-series (8 GB per vCPU)
        assert parse_azure_sku_spec("Standard_E48_v5") == (48, 384.0)
        # F-series (2 GB per vCPU)
        assert parse_azure_sku_spec("Standard_F8s_v2") == (8, 16.0)
        # B-series
        assert parse_azure_sku_spec("Standard_B4ms") == (4, 16.0)
        assert parse_azure_sku_spec("Standard_B2s") == (2, 4.0)

    def test_parse_azure_sku_spec_invalid(self) -> None:
        assert parse_azure_sku_spec("Unknown_Weird_SKU") is None
        assert parse_azure_sku_spec("") is None

    def test_is_standard_linux_ondemand_valid(self) -> None:
        valid_item = {
            "serviceName": "Virtual Machines",
            "type": "Consumption",
            "unitOfMeasure": "1 Hour",
            "productName": "Virtual Machines Dsv3 Series",
            "skuName": "D2s v3",
            "meterName": "D2s v3",
            "retailPrice": 0.096,
        }
        assert is_standard_linux_ondemand(valid_item) is True

    def test_is_standard_linux_ondemand_filters(self) -> None:
        base_item = {
            "serviceName": "Virtual Machines",
            "type": "Consumption",
            "unitOfMeasure": "1 Hour",
            "productName": "Virtual Machines Dsv3 Series",
            "skuName": "D2s v3",
            "meterName": "D2s v3",
            "retailPrice": 0.096,
        }

        # Exclude Windows
        assert (
            is_standard_linux_ondemand(
                {**base_item, "productName": "Virtual Machines Dsv3 Series Windows"}
            )
            is False
        )
        assert (
            is_standard_linux_ondemand({**base_item, "skuName": "D2s v3 Windows"})
            is False
        )

        # Exclude Spot
        assert (
            is_standard_linux_ondemand({**base_item, "skuName": "D2s v3 Spot"})
            is False
        )
        assert (
            is_standard_linux_ondemand({**base_item, "meterName": "D2s v3 Spot"})
            is False
        )

        # Exclude Low Priority
        assert (
            is_standard_linux_ondemand(
                {**base_item, "skuName": "D2s v3 Low Priority"}
            )
            is False
        )

        # Exclude Dedicated Host
        assert (
            is_standard_linux_ondemand(
                {**base_item, "productName": "Dedicated Host Dsv3 Series"}
            )
            is False
        )

        # Exclude non-consumption / reservations
        assert is_standard_linux_ondemand({**base_item, "type": "Reservation"}) is False

        # Exclude non-hourly
        assert (
            is_standard_linux_ondemand({**base_item, "unitOfMeasure": "1 Month"})
            is False
        )

        # Exclude non-VM
        assert (
            is_standard_linux_ondemand({**base_item, "serviceName": "Storage"})
            is False
        )

        # Exclude zero or negative price
        assert is_standard_linux_ondemand({**base_item, "retailPrice": 0.0}) is False
        assert is_standard_linux_ondemand({**base_item, "retailPrice": -0.5}) is False


# ---------------------------------------------------------------------------
# Core Service & Parser Tests
# ---------------------------------------------------------------------------


class TestAzurePricingServiceCore:
    """Test dynamic OData query construction and fixture JSON parsing."""

    def test_get_pricing_url(self) -> None:
        service = AzurePricingService()
        url_eastus = service.get_pricing_url("eastus")
        assert "armRegionName eq 'eastus'" in url_eastus
        assert "serviceName eq 'Virtual Machines'" in url_eastus
        assert "priceType eq 'Consumption'" in url_eastus

        # Alias resolution
        url_alias_us = service.get_pricing_url("us")
        assert "armRegionName eq 'eastus'" in url_alias_us

        url_alias_eu = service.get_pricing_url("eu")
        assert "armRegionName eq 'westeurope'" in url_alias_eu

        url_alias_asia = service.get_pricing_url("asia")
        assert "armRegionName eq 'southeastasia'" in url_alias_asia

    def test_parse_price_list_with_fixture(
        self,
        sample_pricing_json: dict[str, Any],
    ) -> None:
        service = AzurePricingService()
        items = sample_pricing_json["Items"]
        parsed = service.parse_price_list(items, region_code="eastus")

        # In fixture of 11 items:
        # - 7 standard Linux VMs (B1s, B2s, D2s_v3, D4s_v5, D8s_v5, E2s_v5, F2s_v2)
        # - 1 Windows (excluded)
        # - 1 Spot (excluded)
        # - 1 Low Priority (excluded)
        # - 1 Dedicated Host (excluded)
        assert len(parsed) == 7

        sku_names = {p.arm_sku_name for p in parsed}
        assert "Standard_B1s" in sku_names
        assert "Standard_B2s" in sku_names
        assert "Standard_D2s_v3" in sku_names
        assert "Standard_D4s_v5" in sku_names
        assert "Standard_D8s_v5" in sku_names
        assert "Standard_E2s_v5" in sku_names
        assert "Standard_F2s_v2" in sku_names

        # Verify parsed attributes on Standard_D2s_v3
        d2s = next(p for p in parsed if p.arm_sku_name == "Standard_D2s_v3")
        assert d2s.vcpus == 2
        assert d2s.memory_gb == 8.0
        assert d2s.price_per_hour_usd == 0.096
        assert d2s.region_code == "eastus"


# ---------------------------------------------------------------------------
# Instance Selection Tests
# ---------------------------------------------------------------------------


class TestAzureInstanceSelection:
    """Test smallest-instance matching (round-up) and tie-breaking."""

    @pytest.fixture
    def catalogue(
        self,
        sample_pricing_json: dict[str, Any],
    ) -> list[AzureVMInstancePrice]:
        service = AzurePricingService()
        return service.parse_price_list(sample_pricing_json["Items"], "eastus")

    def test_select_smallest_exact_match(
        self,
        catalogue: list[AzureVMInstancePrice],
    ) -> None:
        service = AzurePricingService()
        # 1 vCPU, 1 GB RAM -> B1s
        match = service.select_instance(catalogue, min_vcpus=1, min_memory_gb=1.0)
        assert match.arm_sku_name == "Standard_B1s"

    def test_select_rounds_up_ram(
        self,
        catalogue: list[AzureVMInstancePrice],
    ) -> None:
        service = AzurePricingService()
        # 2 vCPUs, 6 GB RAM -> D2s_v3 (2 vCPU, 8 GB RAM)
        match = service.select_instance(catalogue, min_vcpus=2, min_memory_gb=6.0)
        assert match.arm_sku_name == "Standard_D2s_v3"
        assert match.vcpus >= 2
        assert match.memory_gb >= 6.0

    def test_select_rounds_up_vcpu(
        self,
        catalogue: list[AzureVMInstancePrice],
    ) -> None:
        service = AzurePricingService()
        # 3 vCPUs, 12 GB RAM -> D4s_v5 (4 vCPU, 16 GB RAM)
        match = service.select_instance(catalogue, min_vcpus=3, min_memory_gb=12.0)
        assert match.arm_sku_name == "Standard_D4s_v5"
        assert match.vcpus >= 3
        assert match.memory_gb >= 12.0

    def test_select_memory_optimized(
        self,
        catalogue: list[AzureVMInstancePrice],
    ) -> None:
        service = AzurePricingService()
        # 2 vCPUs, 16 GB RAM -> E2s_v5 (2 vCPU, 16 GB RAM)
        match = service.select_instance(catalogue, min_vcpus=2, min_memory_gb=16.0)
        assert match.arm_sku_name == "Standard_E2s_v5"
        assert match.vcpus == 2
        assert match.memory_gb == 16.0

    def test_fallback_when_spec_exceeds_catalogue(
        self,
        catalogue: list[AzureVMInstancePrice],
    ) -> None:
        service = AzurePricingService()
        # 128 vCPUs, 512 GB RAM -> largest in catalogue (D8s_v5: 8 vCPUs, 32 GB RAM)
        match = service.select_instance(catalogue, min_vcpus=128, min_memory_gb=512.0)
        assert match.arm_sku_name == "Standard_D8s_v5"

    def test_empty_catalogue_raises(self) -> None:
        service = AzurePricingService()
        with pytest.raises(ValueError, match="No instances available"):
            service.select_instance([], min_vcpus=2, min_memory_gb=4.0)


# ---------------------------------------------------------------------------
# Caching & TTL Tests
# ---------------------------------------------------------------------------


class TestAzureTTLAndCaching:
    """Test 24-hour TTL caching behavior and force refresh."""

    @pytest.mark.asyncio
    async def test_cache_hit_avoids_repeated_network_calls(
        self,
        sample_pricing_json: dict[str, Any],
    ) -> None:
        service = AzurePricingService(cache_ttl=timedelta(hours=24))

        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_pricing_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        # First call: cache miss, makes network call
        first_result = await service.fetch_price_list(
            "eastus", client=mock_client
        )
        assert len(first_result) == 7
        assert mock_client.get.call_count == 1

        # Second call: cache hit, no network call
        second_result = await service.fetch_price_list(
            "eastus", client=mock_client
        )
        assert len(second_result) == 7
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(
        self,
        sample_pricing_json: dict[str, Any],
    ) -> None:
        service = AzurePricingService(cache_ttl=timedelta(hours=24))

        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_pricing_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        # Initial call
        await service.fetch_price_list("eastus", client=mock_client)
        assert mock_client.get.call_count == 1

        # Force refresh
        await service.fetch_price_list(
            "eastus", force_refresh=True, client=mock_client
        )
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_expired_cache_refetches(
        self,
        sample_pricing_json: dict[str, Any],
    ) -> None:
        service = AzurePricingService(cache_ttl=timedelta(hours=24))

        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_pricing_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        # Initial call
        await service.fetch_price_list("eastus", client=mock_client)
        assert mock_client.get.call_count == 1

        # Simulate 25 hours elapsed
        from app.services.pricing.azure_pricing_service import _CACHE

        cached_time, cached_data = _CACHE["eastus"]
        _CACHE["eastus"] = (cached_time - timedelta(hours=25), cached_data)

        # Call again: expired cache triggers fresh fetch
        await service.fetch_price_list("eastus", client=mock_client)
        assert mock_client.get.call_count == 2


# ---------------------------------------------------------------------------
# Cost Calculation & Fallback Tests
# ---------------------------------------------------------------------------


class TestAzureCostCalculation:
    """Test get_instance_price computation, storage calculation, and fallback."""

    @pytest.mark.asyncio
    async def test_get_instance_price_deterministic(
        self,
        sample_pricing_json: dict[str, Any],
    ) -> None:
        service = AzurePricingService()

        mock_resp = MagicMock()
        mock_resp.json.return_value = sample_pricing_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp

        estimate = await service.get_instance_price(
            region_code="eastus",
            vcpus=2,
            memory_gb=8.0,
            hours_per_month=730.0,
            storage_gb=100,
            client=mock_client,
        )

        assert estimate.instance_type == "Standard_D2s_v3"
        assert estimate.vcpus == 2
        assert estimate.memory_gb == 8.0
        assert estimate.price_per_hour_usd == 0.096

        expected_compute = round(0.096 * 730, 4)  # 70.08
        expected_storage = round(100 * 0.0576, 4)  # 5.76
        expected_total = round(expected_compute + expected_storage, 4)  # 75.84

        assert estimate.monthly_cost_low == expected_compute
        assert estimate.monthly_cost_high == expected_compute
        assert estimate.storage_monthly_usd == expected_storage
        assert estimate.total_monthly_usd == expected_total

    @pytest.mark.asyncio
    async def test_network_failure_uses_fallback_catalogue(self) -> None:
        service = AzurePricingService()

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection timed out")

        estimate = await service.get_instance_price(
            region_code="eastus",
            vcpus=2,
            memory_gb=4.0,
            storage_gb=50,
            client=mock_client,
        )

        assert estimate.instance_type == "Standard_B2s"
        assert estimate.vcpus == 2
        assert estimate.memory_gb == 4.0
        assert estimate.price_per_hour_usd == 0.0416
        assert estimate.storage_gb == 50
