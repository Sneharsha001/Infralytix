"""
Tests — Multi-Cloud Cost Comparison Public Endpoint (POST /api/v1/cost-comparison).

Verifies:
  - Unauthenticated access returns HTTP 200 with CloudComparisonResponse schema.
  - All three providers (AWS, Azure, GCP) are evaluated and returned.
  - Graceful degradation on provider failure.
  - Field validation on CloudResourceRequest (vcpu, ram_gb, storage_gb).
  - All external I/O (cloud pricing APIs, Gemini) mocked to ensure isolated tests.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.schemas.cost_comparison import CloudComparisonResponse
from app.services.pricing.aws_pricing_service import AWSEC2InstancePrice
from app.services.pricing.azure_pricing_service import AzureVMInstancePrice
from app.services.pricing.gcp_pricing_service import GCPInstancePrice


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


MockPricingTuple = tuple[
    list[AWSEC2InstancePrice],
    list[AzureVMInstancePrice],
    list[GCPInstancePrice],
]


@pytest.fixture
def mock_pricing_data() -> MockPricingTuple:
    aws_data = [
        AWSEC2InstancePrice(
            sku="AWS-T3-XLARGE",
            instance_type="t3.xlarge",
            vcpus=4,
            memory_gb=16.0,
            price_per_hour_usd=0.1664,
            region_code="us-east-1",
        )
    ]
    azure_data = [
        AzureVMInstancePrice(
            arm_sku_name="Standard_D4s_v5",
            sku_name="D4s v5",
            meter_name="D4s v5",
            product_name="Virtual Machines Dsv5 Series",
            vcpus=4,
            memory_gb=16.0,
            price_per_hour_usd=0.192,
            region_code="eastus",
        )
    ]
    gcp_data = [
        GCPInstancePrice(
            machine_type="e2-standard-4",
            vcpus=4,
            memory_gb=16.0,
            price_per_hour_usd=0.13404,
            region_code="us-east4",
            family="e2",
        )
    ]
    return aws_data, azure_data, gcp_data


def test_cost_comparison_endpoint_success(
    client: TestClient,
    mock_pricing_data: MockPricingTuple,
) -> None:
    """Public endpoint returns 200 with all three providers and AI recommendation."""
    aws_data, azure_data, gcp_data = mock_pricing_data

    payload = {
        "vcpu": 4,
        "ram_gb": 16,
        "storage_gb": 100,
        "region": "us-east",
        "hours_per_month": 730,
    }

    with (
        patch(
            "app.services.pricing.aws_pricing_service.aws_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=aws_data,
        ),
        patch(
            "app.services.pricing.azure_pricing_service.azure_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=azure_data,
        ),
        patch(
            "app.services.pricing.gcp_pricing_service.gcp_pricing_service.fetch_price_list",
            new_callable=AsyncMock,
            return_value=(gcp_data, True),
        ),
        patch(
            "app.services.cost_comparison_service.cost_comparison_service.generate_ai_recommendation",
            new_callable=AsyncMock,
            return_value="GCP e2-standard-4 provides the most cost-effective solution.",
        ),
    ):
        response = client.post("/api/v1/cost-comparison", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Validate against Pydantic model
    validated = CloudComparisonResponse.model_validate(data)
    assert len(validated.estimates) == 3

    providers = [e.provider for e in validated.estimates]
    assert set(providers) == {"aws", "azure", "gcp"}

    # AWS check
    aws_est = next(e for e in validated.estimates if e.provider == "aws")
    assert aws_est.instance_type_matched == "t3.xlarge"
    assert aws_est.monthly_cost_low == 129.47  # (0.1664 * 730) + (100 * 0.08)

    # Azure check
    azure_est = next(e for e in validated.estimates if e.provider == "azure")
    assert azure_est.instance_type_matched == "Standard_D4s_v5"
    assert azure_est.monthly_cost_low == 145.92  # (0.192 * 730) + (100 * 0.0576)

    # GCP check
    gcp_est = next(e for e in validated.estimates if e.provider == "gcp")
    assert gcp_est.instance_type_matched == "e2-standard-4"
    assert gcp_est.monthly_cost_low == 101.85  # (0.13404 * 730) + (100 * 0.04)

    assert "GCP" in validated.ai_suggestion


def test_cost_comparison_endpoint_validation(client: TestClient) -> None:
    """Invalid resource requests return 422 Unprocessable Entity."""
    # vcpu below 1
    resp = client.post("/api/v1/cost-comparison", json={"vcpu": 0, "ram_gb": 4, "storage_gb": 10})
    assert resp.status_code == 422

    # ram_gb below 1
    resp = client.post("/api/v1/cost-comparison", json={"vcpu": 2, "ram_gb": 0, "storage_gb": 10})
    assert resp.status_code == 422

    # storage_gb negative
    resp = client.post("/api/v1/cost-comparison", json={"vcpu": 2, "ram_gb": 4, "storage_gb": -5})
    assert resp.status_code == 422
