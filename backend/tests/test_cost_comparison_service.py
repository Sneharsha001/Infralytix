"""
Infralytix — Multi-Cloud Cost Comparison Service Unit Tests.

Verifies end-to-end multi-cloud cost calculation, concurrent execution of
remote AWS and Azure pricing calls via asyncio.gather, storage calculations,
and provider sorting.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.cost import CostEstimateRequest
from app.schemas.cost_comparison import CloudComparisonResponse, CloudResourceRequest
from app.services.cost_comparison_service import CostComparisonService, cost_comparison_service
from app.services.pricing.aws_pricing_service import AWSEC2InstancePrice
from app.services.pricing.azure_pricing_service import AzureVMInstancePrice
from app.services.pricing.gcp_pricing_service import (
    GCPInstancePrice,
    gcp_pricing_service,
)


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


@pytest.mark.asyncio
async def test_cost_comparison_partial_failure_azure(
    mock_aws_instances: list[AWSEC2InstancePrice],
) -> None:
    """
    If Azure live API fails, it must return an error note on Azure's result
    without crashing or substituting silent static data.
    """
    service = CostComparisonService()
    req = CostEstimateRequest(
        cpu_cores=4,
        memory_gb=16,
        storage_gb=100,
        hours_per_month=730,
        providers=["aws", "azure", "gcp"],
        region_preference="us",
        workload_label="azure-failure-test",
    )

    with (
        patch(
            "app.services.pricing.aws_pricing_service.aws_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=mock_aws_instances,
        ),
        patch(
            "app.services.pricing.azure_pricing_service.azure_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Azure API 503 Service Unavailable"),
        ),
    ):
        estimates = await service.compare(req)

    assert len(estimates) == 3
    azure_est = next(e for e in estimates if e.provider == "azure")
    assert azure_est.instance.instance_type == "unavailable"
    assert any("unavailable" in n.lower() or "failed" in n.lower() for n in azure_est.notes)
    # Valid providers must be sorted before unavailable provider
    assert estimates[-1].provider == "azure"


@pytest.mark.asyncio
async def test_cost_comparison_partial_failure_aws(
    mock_azure_instances: list[AzureVMInstancePrice],
) -> None:
    """
    If AWS live API fails, it must return an error note on AWS's result
    without crashing or substituting silent static data.
    """
    service = CostComparisonService()
    req = CostEstimateRequest(
        cpu_cores=4,
        memory_gb=16,
        storage_gb=100,
        hours_per_month=730,
        providers=["aws", "azure", "gcp"],
        region_preference="us",
        workload_label="aws-failure-test",
    )

    with (
        patch(
            "app.services.pricing.aws_pricing_service.aws_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            side_effect=RuntimeError("AWS Pricing API connection error"),
        ),
        patch(
            "app.services.pricing.azure_pricing_service.azure_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=mock_azure_instances,
        ),
    ):
        estimates = await service.compare(req)

    assert len(estimates) == 3
    aws_est = next(e for e in estimates if e.provider == "aws")
    assert aws_est.instance.instance_type == "unavailable"
    assert any("unavailable" in n.lower() or "failed" in n.lower() for n in aws_est.notes)
    # Valid providers must be sorted before unavailable provider
    assert estimates[-1].provider == "aws"


# =============================================================================
# Multi-Cloud CloudResourceRequest & compare_clouds Tests
# =============================================================================


@pytest.fixture
def mock_gcp_instances() -> list[GCPInstancePrice]:
    return [
        GCPInstancePrice(
            machine_type="e2-standard-2",
            vcpus=2,
            memory_gb=8.0,
            price_per_hour_usd=0.06702,
            region_code="us-east4",
            family="e2",
        ),
        GCPInstancePrice(
            machine_type="e2-standard-4",
            vcpus=4,
            memory_gb=16.0,
            price_per_hour_usd=0.13404,
            region_code="us-east4",
            family="e2",
        ),
    ]


@pytest.mark.asyncio
async def test_cloud_comparison_all_three_succeeding(
    mock_aws_instances: list[AWSEC2InstancePrice],
    mock_azure_instances: list[AzureVMInstancePrice],
    mock_gcp_instances: list[GCPInstancePrice],
) -> None:
    """
    Normal case: all three cloud providers succeed.
    Verifies instance matching, storage line items, sorting, and AI suggestion.
    """
    service = CostComparisonService()
    req = CloudResourceRequest(
        vcpu=4,
        ram_gb=16,
        storage_gb=100,
        region="us-east",
        hours_per_month=730,
    )

    with (
        patch(
            "app.services.pricing.aws_pricing_service.aws_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=mock_aws_instances,
        ),
        patch(
            "app.services.pricing.azure_pricing_service.azure_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=mock_azure_instances,
        ),
        patch(
            "app.services.pricing.gcp_pricing_service.gcp_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=(mock_gcp_instances, True),
        ),
        patch.object(
            service,
            "generate_ai_recommendation",
            new_callable=AsyncMock,
            return_value="GCP provides the most cost-effective option for this workload.",
        ),
    ):
        resp = await service.compare_clouds(req)

    assert isinstance(resp, CloudComparisonResponse)
    assert len(resp.estimates) == 3

    providers = [e.provider for e in resp.estimates]
    assert set(providers) == {"aws", "azure", "gcp"}

    # All providers succeeded with error=None and positive monthly cost
    for est in resp.estimates:
        assert est.error is None
        assert est.monthly_cost_low > 0.0
        assert est.monthly_cost_high == est.monthly_cost_low

    # Verify sorting cheapest first
    costs = [e.monthly_cost_low for e in resp.estimates]
    assert costs == sorted(costs)

    # AWS: 4 vCPU 16GB -> t3.xlarge @ 0.1664 * 730 = 121.47 + 8.00 = 129.47
    aws_est = next(e for e in resp.estimates if e.provider == "aws")
    assert aws_est.instance_type_matched == "t3.xlarge"
    assert "EBS gp3" in (aws_est.notes or "")

    # Azure: 4 vCPU 16GB -> Standard_D4s_v5 @ 0.192 * 730 = 140.16 + 5.76 = 145.92
    azure_est = next(e for e in resp.estimates if e.provider == "azure")
    assert azure_est.instance_type_matched == "Standard_D4s_v5"
    assert "Azure Premium SSD" in (azure_est.notes or "")

    # GCP: 4 vCPU 16GB -> e2-standard-4 @ 0.13404 * 730 = 97.85 + 4.00 = 101.85
    gcp_est = next(e for e in resp.estimates if e.provider == "gcp")
    assert gcp_est.instance_type_matched == "e2-standard-4"
    assert "pd-balanced" in (gcp_est.notes or "")

    assert "GCP" in resp.ai_suggestion


@pytest.mark.asyncio
async def test_cloud_comparison_one_provider_failing_gracefully(
    mock_aws_instances: list[AWSEC2InstancePrice],
    mock_gcp_instances: list[GCPInstancePrice],
) -> None:
    """
    Partial failure: Azure fails, AWS and GCP succeed.
    The response must contain 3 estimates, Azure has error set and $0.00 cost,
    and valid providers appear first.
    """
    service = CostComparisonService()
    req = CloudResourceRequest(
        vcpu=4,
        ram_gb=16,
        storage_gb=100,
        region="us-east",
        hours_per_month=730,
    )

    with (
        patch(
            "app.services.pricing.aws_pricing_service.aws_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=mock_aws_instances,
        ),
        patch(
            "app.services.pricing.azure_pricing_service.azure_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Azure Retail API 500 Internal Server Error"),
        ),
        patch(
            "app.services.pricing.gcp_pricing_service.gcp_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=(mock_gcp_instances, True),
        ),
    ):
        resp = await service.compare_clouds(req)

    assert len(resp.estimates) == 3

    # Azure should have error set
    azure_est = next(e for e in resp.estimates if e.provider == "azure")
    assert azure_est.error is not None
    assert "failed" in azure_est.error.lower()
    assert azure_est.instance_type_matched == "unavailable"
    assert azure_est.monthly_cost_low == 0.0

    # AWS and GCP must succeed
    aws_est = next(e for e in resp.estimates if e.provider == "aws")
    assert aws_est.error is None
    assert aws_est.monthly_cost_low > 0.0

    gcp_est = next(e for e in resp.estimates if e.provider == "gcp")
    assert gcp_est.error is None
    assert gcp_est.monthly_cost_low > 0.0

    # The failed provider (Azure) must be sorted at the end
    assert resp.estimates[-1].provider == "azure"


@pytest.mark.asyncio
async def test_cloud_comparison_gcp_fallback_when_key_unset() -> None:
    """
    When settings.GCP_API_KEY is empty, GCPPricingService uses the static reference
    dataset and sets the explicit non-live reference note.
    """
    with patch("app.services.pricing.gcp_pricing_service.settings.GCP_API_KEY", ""):
        instances, is_static = await gcp_pricing_service.fetch_price_list("us-east4")
        assert is_static is True
        assert len(instances) >= 6

        # Test full get_estimate method
        inst, comp, stor, total, notes, is_stat = await gcp_pricing_service.get_estimate(
            vcpu=4,
            ram_gb=16,
            storage_gb=100,
            region="us-east",
            hours_per_month=730,
        )
        assert is_stat is True
        assert "Static reference pricing — live GCP API not configured" in notes
        assert inst.machine_type == "e2-standard-4"
        assert total > 0.0


@pytest.mark.asyncio
async def test_cloud_comparison_concurrent_execution_in_parallel(
    mock_aws_instances: list[AWSEC2InstancePrice],
    mock_azure_instances: list[AzureVMInstancePrice],
    mock_gcp_instances: list[GCPInstancePrice],
) -> None:
    """
    Verify that AWS, Azure, and GCP fetch calls run concurrently via asyncio.gather.
    Each mock sleeps 0.15s; if sequential it would take >=0.45s; if parallel it completes in <0.30s.
    """
    service = CostComparisonService()
    req = CloudResourceRequest(vcpu=2, ram_gb=4, storage_gb=50, region="us-east")

    async def _delayed_aws(*args: object, **kwargs: object) -> list[AWSEC2InstancePrice]:
        await asyncio.sleep(0.12)
        return mock_aws_instances

    async def _delayed_azure(*args: object, **kwargs: object) -> list[AzureVMInstancePrice]:
        await asyncio.sleep(0.12)
        return mock_azure_instances

    async def _delayed_gcp(*args: object, **kwargs: object) -> tuple[list[GCPInstancePrice], bool]:
        await asyncio.sleep(0.12)
        return mock_gcp_instances, True

    with (
        patch(
            "app.services.pricing.aws_pricing_service.aws_pricing_service.fetch_price_list",
            side_effect=_delayed_aws,
        ),
        patch(
            "app.services.pricing.azure_pricing_service.azure_pricing_service.fetch_price_list",
            side_effect=_delayed_azure,
        ),
        patch(
            "app.services.pricing.gcp_pricing_service.gcp_pricing_service.fetch_price_list",
            side_effect=_delayed_gcp,
        ),
        patch.object(
            service,
            "generate_ai_recommendation",
            new_callable=AsyncMock,
            return_value="Mock recommendation.",
        ),
    ):
        t0 = time.perf_counter()
        resp = await service.compare_clouds(req)
        elapsed = time.perf_counter() - t0

    assert len(resp.estimates) == 3
    # Parallel execution of 3 x 0.12s tasks must complete in well under the sequential sum of 0.36s
    assert elapsed < 0.28, f"Expected parallel execution under 0.28s, took {elapsed:.2f}s"
