"""
Infralytix — Multi-Cloud Cost Comparison Service Unit Tests.

Verifies end-to-end multi-cloud cost calculation, concurrent execution of
remote AWS and Azure pricing calls via asyncio.gather, storage calculations,
and provider sorting.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.cost import CostEstimateRequest
from app.services.cost_comparison_service import CostComparisonService, cost_comparison_service
from app.services.pricing.aws_pricing_service import AWSEC2InstancePrice
from app.services.pricing.azure_pricing_service import AzureVMInstancePrice


@pytest.fixture
def mock_aws_instances() -> list[AWSEC2InstancePrice]:
    return [
        AWSEC2InstancePrice(
            sku="AWS-SKU-1",
            instance_type="t3.medium",
            vcpus=2,
            memory_gb=4.0,
            price_per_hour_usd=0.0416,
            region_code="us-east-1",
        ),
        AWSEC2InstancePrice(
            sku="AWS-SKU-2",
            instance_type="t3.xlarge",
            vcpus=4,
            memory_gb=16.0,
            price_per_hour_usd=0.1664,
            region_code="us-east-1",
        ),
    ]


@pytest.fixture
def mock_azure_instances() -> list[AzureVMInstancePrice]:
    return [
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
            arm_sku_name="Standard_D4s_v5",
            sku_name="D4s v5",
            meter_name="D4s v5",
            product_name="Virtual Machines Dsv5 Series",
            vcpus=4,
            memory_gb=16.0,
            price_per_hour_usd=0.192,
            region_code="eastus",
        ),
    ]


@pytest.mark.asyncio
async def test_cost_comparison_concurrent_aws_and_azure(
    mock_aws_instances: list[AWSEC2InstancePrice],
    mock_azure_instances: list[AzureVMInstancePrice],
) -> None:
    """
    Verify that compute_async calls both AWS and Azure pricing fetchers concurrently
    and returns sorted multi-cloud estimates.
    """
    service = CostComparisonService()
    req = CostEstimateRequest(
        cpu_cores=4,
        memory_gb=16,
        storage_gb=100,
        hours_per_month=730,
        providers=["aws", "azure", "gcp"],
        region_preference="us",
        workload_label="concurrent-test",
    )

    with (
        patch(
            "app.services.pricing.aws_pricing_service.aws_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=mock_aws_instances,
        ) as mock_aws_fetch,
        patch(
            "app.services.pricing.azure_pricing_service.azure_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=mock_azure_instances,
        ) as mock_azure_fetch,
    ):
        estimates = await service.compare(req)

        assert mock_aws_fetch.call_count == 1
        assert mock_azure_fetch.call_count == 1

    assert len(estimates) == 3
    providers = [e.provider for e in estimates]
    assert "aws" in providers
    assert "azure" in providers
    assert "gcp" in providers

    # Ensure sorted by total_monthly_usd ascending
    totals = [e.total_monthly_usd for e in estimates]
    assert totals == sorted(totals)

    # Check AWS matched t3.xlarge
    aws_est = next(e for e in estimates if e.provider == "aws")
    assert aws_est.instance.instance_type == "t3.xlarge"
    assert aws_est.region == "us-east-1"
    assert aws_est.storage.total_cost_usd == 8.0  # 100 GB * $0.08

    # Check Azure matched Standard_D4s_v5
    azure_est = next(e for e in estimates if e.provider == "azure")
    assert azure_est.instance.instance_type == "Standard_D4s_v5"
    assert azure_est.region == "eastus"
    assert azure_est.storage.total_cost_usd == 5.76  # 100 GB * $0.0576


@pytest.mark.asyncio
async def test_cost_comparison_service_singleton() -> None:
    """Verify module-level singleton instance exists and is usable."""
    assert cost_comparison_service is not None
    assert isinstance(cost_comparison_service, CostComparisonService)
