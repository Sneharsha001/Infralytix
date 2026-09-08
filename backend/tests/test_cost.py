"""
Tests — Multi-Cloud Cost Comparison Feature.

Test strategy:
  - ALL external I/O is mocked (no live Gemini calls, no live pricing APIs).
  - Uses unittest.mock.patch per test_health.py / test_agents.py pattern.
  - Covers: endpoint contract, validation, service logic, AI path, fallback path.

Fixtures:
  - auth_client: TestClient with a pre-authenticated user session
    (mocked auth via dependency_overrides — same technique as test_auth.py).
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.middlewares.auth_middleware import get_current_user
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.user import User, UserRole

# =============================================================================
# Helpers
# =============================================================================


def _make_user(**kwargs: Any) -> User:
    """Build a deterministic mock User for auth override."""
    uid = uuid.uuid4()
    return User(
        id=uid,
        email=kwargs.get("email", "cost@test.com"),
        name=kwargs.get("name", "Cost Tester"),
        role=kwargs.get("role", UserRole.USER),
        is_active=True,
        hashed_password="not-used",
    )


def _make_completed_cost_run(user_id: uuid.UUID, result: dict[str, Any]) -> AgentRun:
    """Build a mock completed AgentRun for cost tests."""
    run = AgentRun()
    run.id = uuid.uuid4()
    run.project_id = user_id
    run.agent_type = "cost"
    run.status = AgentRunStatus.COMPLETED
    run.output_data = {"result": result, "workload_label": "Test Workload"}
    from datetime import UTC, datetime

    run.created_at = datetime.now(UTC)
    run.updated_at = datetime.now(UTC)
    return run


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock AsyncSession — satisfies get_db dependency."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def test_user() -> User:
    return _make_user()


@pytest.fixture
def auth_client(mock_db: AsyncMock, test_user: User) -> TestClient:
    """
    TestClient with:
      - get_db overridden to yield mock_db
      - get_current_user overridden to return test_user
    """
    from app.database.session import get_db

    app = create_application()

    async def _override_get_db() -> Any:  # type: ignore[override]
        yield mock_db

    async def _override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client() -> TestClient:
    """TestClient with NO auth override (tests 401 responses)."""
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(autouse=True)
def mock_cloud_pricing_services() -> Any:
    """Ensure no live network calls to AWS or Azure pricing APIs during cost tests."""
    from datetime import UTC, datetime

    from app.services.pricing.aws_pricing_service import (
        _CACHE as _AWS_CACHE,
    )
    from app.services.pricing.aws_pricing_service import (
        AWSEC2InstancePrice,
    )
    from app.services.pricing.azure_pricing_service import (
        _CACHE as _AZURE_CACHE,
    )
    from app.services.pricing.azure_pricing_service import (
        AzureVMInstancePrice,
    )

    mock_aws_instances = [
        AWSEC2InstancePrice(
            sku="AWS-T3-MICRO",
            instance_type="t3.micro",
            vcpus=1,
            memory_gb=1.0,
            price_per_hour_usd=0.0104,
            region_code="us-east-1",
        ),
        AWSEC2InstancePrice(
            sku="AWS-T3-SMALL",
            instance_type="t3.small",
            vcpus=2,
            memory_gb=2.0,
            price_per_hour_usd=0.0208,
            region_code="us-east-1",
        ),
        AWSEC2InstancePrice(
            sku="AWS-T3-MEDIUM",
            instance_type="t3.medium",
            vcpus=2,
            memory_gb=4.0,
            price_per_hour_usd=0.0416,
            region_code="us-east-1",
        ),
        AWSEC2InstancePrice(
            sku="AWS-T3-XLARGE",
            instance_type="t3.xlarge",
            vcpus=4,
            memory_gb=16.0,
            price_per_hour_usd=0.1664,
            region_code="us-east-1",
        ),
        AWSEC2InstancePrice(
            sku="AWS-T3-2XLARGE",
            instance_type="t3.2xlarge",
            vcpus=8,
            memory_gb=32.0,
            price_per_hour_usd=0.3328,
            region_code="us-east-1",
        ),
    ]

    mock_azure_instances = [
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
    ]

    now = datetime.now(UTC)
    _AWS_CACHE["us-east-1"] = (now, mock_aws_instances)
    _AZURE_CACHE["eastus"] = (now, mock_azure_instances)

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
    ):
        yield

    _AWS_CACHE.clear()
    _AZURE_CACHE.clear()


# =============================================================================
# Minimal valid request body
# =============================================================================

VALID_REQUEST: dict[str, Any] = {
    "cpu_cores": 4,
    "memory_gb": 16,
    "storage_gb": 100,
    "hours_per_month": 730,
    "providers": ["aws", "gcp", "azure"],
    "region_preference": "us",
    "workload_label": "pytest-test",
}


# =============================================================================
# Auth Guard Tests
# =============================================================================


class TestAuthGuards:
    """Protected endpoints require auth, but public cost estimation does not."""

    def test_estimate_unauthenticated_allowed(self, unauth_client: TestClient) -> None:
        """Cost estimation does not require authentication per spec."""
        with patch(
            "app.api.v1.endpoints.cost.CostAIService.suggest",
            new_callable=AsyncMock,
            return_value="Rule-based suggestion for public user.",
        ):
            response = unauth_client.post("/api/v1/cost/estimate", json=VALID_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert len(data["result"]["providers"]) == 3

    def test_cost_comparison_alias_unauthenticated_allowed(self, unauth_client: TestClient) -> None:
        """Direct /cost-comparison alias also allows unauthenticated calls."""
        response = unauth_client.post("/api/v1/cost-comparison", json=VALID_REQUEST)
        assert response.status_code == 200
        data = response.json()
        assert "estimates" in data or "result" in data

    def test_list_requires_auth(self, unauth_client: TestClient) -> None:
        """Saved estimate history is private to the authenticated user."""
        response = unauth_client.get("/api/v1/cost/estimates")
        assert response.status_code == 401

    def test_get_by_id_requires_auth(self, unauth_client: TestClient) -> None:
        """Retrieving saved estimate runs requires authentication."""
        fake_id = str(uuid.uuid4())
        response = unauth_client.get(f"/api/v1/cost/estimates/{fake_id}")
        assert response.status_code == 401


# =============================================================================
# POST /cost/estimate — Success
# =============================================================================


class TestCreateEstimate:
    """Tests for the POST /cost/estimate endpoint."""

    def _make_mock_run(self, user_id: uuid.UUID) -> MagicMock:
        """Build a mock AgentRun object returned by the repository."""
        from datetime import UTC, datetime

        run = MagicMock()
        run.id = uuid.uuid4()
        run.project_id = user_id
        run.agent_type = "cost"
        run.status = AgentRunStatus.COMPLETED
        run.created_at = datetime.now(UTC)
        run.updated_at = datetime.now(UTC)
        run.output_data = {}
        return run

    def test_returns_200_with_all_three_providers(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        """A valid request must return 200 and include all three providers."""
        mock_run = self._make_mock_run(test_user.id)

        with (
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.create",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.update_status",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.CostAIService.suggest",
                new_callable=AsyncMock,
                return_value="AWS is recommended for this workload.",
            ),
        ):
            response = auth_client.post("/api/v1/cost/estimate", json=VALID_REQUEST)

        assert response.status_code == 200
        body = response.json()
        assert "result" in body
        assert "providers" in body["result"]

        provider_names = {p["provider"] for p in body["result"]["providers"]}
        assert provider_names == {"aws", "gcp", "azure"}

    def test_response_schema_fields_present(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        """Response must contain id, result, created_at, workload_label."""
        mock_run = self._make_mock_run(test_user.id)

        with (
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.create",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.update_status",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.CostAIService.suggest",
                new_callable=AsyncMock,
                return_value="GCP is best value.",
            ),
        ):
            response = auth_client.post("/api/v1/cost/estimate", json=VALID_REQUEST)

        body = response.json()
        assert "id" in body
        assert "result" in body
        assert "created_at" in body
        assert "workload_label" in body

    def test_ai_suggestion_field_present(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        """The ai_suggestion field must be a non-empty string."""
        mock_run = self._make_mock_run(test_user.id)
        expected_suggestion = "GCP offers the best value for this workload."

        with (
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.create",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.update_status",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.CostAIService.suggest",
                new_callable=AsyncMock,
                return_value=expected_suggestion,
            ),
        ):
            response = auth_client.post("/api/v1/cost/estimate", json=VALID_REQUEST)

        body = response.json()
        assert body["result"]["ai_suggestion"] == expected_suggestion

    def test_cheapest_provider_matches_sorted_list(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        """cheapest_provider must match the first (cheapest) entry in providers."""
        mock_run = self._make_mock_run(test_user.id)

        with (
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.create",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.update_status",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.CostAIService.suggest",
                new_callable=AsyncMock,
                return_value="Cheapest is best.",
            ),
        ):
            response = auth_client.post("/api/v1/cost/estimate", json=VALID_REQUEST)

        result = response.json()["result"]
        cheapest_listed = result["providers"][0]["provider"]
        assert result["cheapest_provider"] == cheapest_listed

    def test_single_provider_subset_allowed(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        """A request with only one provider must return exactly one estimate."""
        mock_run = self._make_mock_run(test_user.id)
        body = {**VALID_REQUEST, "providers": ["aws"]}

        with (
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.create",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.AgentRunRepository.update_status",
                new_callable=AsyncMock,
                return_value=mock_run,
            ),
            patch(
                "app.api.v1.endpoints.cost.CostAIService.suggest",
                new_callable=AsyncMock,
                return_value="Only AWS requested.",
            ),
        ):
            response = auth_client.post("/api/v1/cost/estimate", json=body)

        assert response.status_code == 200
        providers = response.json()["result"]["providers"]
        assert len(providers) == 1
        assert providers[0]["provider"] == "aws"


# =============================================================================
# POST /cost/estimate — Validation
# =============================================================================


class TestCreateEstimateValidation:
    """Input validation tests — Pydantic should reject bad inputs with 422."""

    def test_cpu_below_minimum_rejected(self, auth_client: TestClient) -> None:
        body = {**VALID_REQUEST, "cpu_cores": 0}
        response = auth_client.post("/api/v1/cost/estimate", json=body)
        assert response.status_code == 422

    def test_memory_below_minimum_rejected(self, auth_client: TestClient) -> None:
        body = {**VALID_REQUEST, "memory_gb": 0}
        response = auth_client.post("/api/v1/cost/estimate", json=body)
        assert response.status_code == 422

    def test_empty_providers_list_rejected(self, auth_client: TestClient) -> None:
        body = {**VALID_REQUEST, "providers": []}
        response = auth_client.post("/api/v1/cost/estimate", json=body)
        assert response.status_code == 422

    def test_invalid_provider_name_rejected(self, auth_client: TestClient) -> None:
        body = {**VALID_REQUEST, "providers": ["digitalocean"]}
        response = auth_client.post("/api/v1/cost/estimate", json=body)
        assert response.status_code == 422

    def test_invalid_region_rejected(self, auth_client: TestClient) -> None:
        body = {**VALID_REQUEST, "region_preference": "mars"}
        response = auth_client.post("/api/v1/cost/estimate", json=body)
        assert response.status_code == 422


# =============================================================================
# GET /cost/estimates — List
# =============================================================================


class TestListEstimates:
    """Tests for the GET /cost/estimates endpoint."""

    def test_returns_200_with_empty_list(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        with patch(
            "app.api.v1.endpoints.cost.AgentRunRepository.list_by_project",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = auth_client.get("/api/v1/cost/estimates")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_completed_runs_only(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        """Only completed cost runs must appear in the list."""
        completed_result = {
            "providers": [
                {
                    "provider": "gcp",
                    "provider_display": "Google Cloud Platform",
                    "region": "us-central1",
                    "instance": {
                        "instance_type": "e2-standard-4",
                        "vcpus": 4,
                        "memory_gb": 16.0,
                        "price_per_hour_usd": 0.134,
                    },
                    "compute_monthly_usd": 97.82,
                    "storage": {
                        "storage_type": "pd-balanced",
                        "price_per_gb_month_usd": 0.04,
                        "total_cost_usd": 4.0,
                    },
                    "total_monthly_usd": 101.82,
                    "notes": [],
                }
            ],
            "cheapest_provider": "gcp",
            "ai_suggestion": "GCP is best.",
        }
        completed_run = _make_completed_cost_run(test_user.id, completed_result)

        # Build a FAILED run that should NOT appear
        failed_run = MagicMock()
        failed_run.agent_type = "cost"
        failed_run.status = AgentRunStatus.FAILED
        failed_run.output_data = None

        with patch(
            "app.api.v1.endpoints.cost.AgentRunRepository.list_by_project",
            new_callable=AsyncMock,
            return_value=[completed_run, failed_run],
        ):
            response = auth_client.get("/api/v1/cost/estimates")

        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["cheapest_provider"] == "gcp"


# =============================================================================
# GET /cost/estimates/{run_id} — Single Estimate
# =============================================================================


class TestGetEstimate:
    """Tests for the GET /cost/estimates/{run_id} endpoint."""

    def test_returns_404_for_unknown_id(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        with patch(
            "app.api.v1.endpoints.cost.AgentRunRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = auth_client.get(f"/api/v1/cost/estimates/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_returns_404_for_another_users_run(
        self,
        auth_client: TestClient,
        test_user: User,
    ) -> None:
        """404-masking: another user's run must not be visible."""
        other_user_run = MagicMock()
        other_user_run.agent_type = "cost"
        other_user_run.project_id = uuid.uuid4()  # different user ID
        other_user_run.output_data = {"result": {}, "workload_label": ""}

        with patch(
            "app.api.v1.endpoints.cost.AgentRunRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=other_user_run,
        ):
            response = auth_client.get(f"/api/v1/cost/estimates/{uuid.uuid4()}")
        assert response.status_code == 404


# =============================================================================
# Unit Tests — CostCalculatorService
# =============================================================================


class TestCostCalculatorService:
    """Unit tests for the pure service layer — no HTTP, no DB."""

    def test_all_three_providers_returned(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_service import CostCalculatorService

        req = CostEstimateRequest(
            cpu_cores=4,
            memory_gb=16,
            storage_gb=100,
            providers=["aws", "gcp", "azure"],
        )
        results = CostCalculatorService().compute(req)
        providers = {r.provider for r in results}
        assert providers == {"aws", "gcp", "azure"}

    def test_results_sorted_cheapest_first(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_service import CostCalculatorService

        req = CostEstimateRequest(
            cpu_cores=4,
            memory_gb=16,
            storage_gb=100,
            providers=["aws", "gcp", "azure"],
        )
        results = CostCalculatorService().compute(req)
        totals = [r.total_monthly_usd for r in results]
        assert totals == sorted(totals)

    def test_selected_instance_meets_minimum_requirements(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_service import CostCalculatorService

        req = CostEstimateRequest(
            cpu_cores=8,
            memory_gb=32,
            storage_gb=50,
            providers=["aws"],
        )
        results = CostCalculatorService().compute(req)
        est = results[0]
        assert est.instance.vcpus >= 8
        assert est.instance.memory_gb >= 32

    def test_zero_storage_allowed(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_service import CostCalculatorService

        req = CostEstimateRequest(
            cpu_cores=2,
            memory_gb=4,
            storage_gb=0,
            providers=["gcp"],
        )
        results = CostCalculatorService().compute(req)
        assert results[0].storage.total_cost_usd == 0.0

    def test_compute_monthly_cost_correct(self) -> None:
        """compute_monthly = price_per_hour * hours_per_month (approximately)."""
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_service import CostCalculatorService

        req = CostEstimateRequest(
            cpu_cores=2,
            memory_gb=4,
            storage_gb=0,
            hours_per_month=100.0,
            providers=["aws"],
        )
        results = CostCalculatorService().compute(req)
        est = results[0]
        expected = round(est.instance.price_per_hour_usd * 100.0, 4)
        assert abs(est.compute_monthly_usd - expected) < 0.01

    def test_total_is_compute_plus_storage(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_service import CostCalculatorService

        req = CostEstimateRequest(
            cpu_cores=4,
            memory_gb=8,
            storage_gb=200,
            providers=["azure"],
        )
        results = CostCalculatorService().compute(req)
        est = results[0]
        expected_total = round(est.compute_monthly_usd + est.storage.total_cost_usd, 4)
        assert abs(est.total_monthly_usd - expected_total) < 0.01


# =============================================================================
# Unit Tests — CostAIService (mock fallback path)
# =============================================================================


class TestCostAIServiceFallback:
    """Unit tests for the rule-based suggestion fallback."""

    def _build_estimates(
        self,
        cheapest_provider: str = "gcp",
    ) -> list:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_service import CostCalculatorService

        req = CostEstimateRequest(
            cpu_cores=4,
            memory_gb=16,
            storage_gb=50,
            providers=["aws", "gcp", "azure"],
        )
        estimates = CostCalculatorService().compute(req)
        return estimates

    @pytest.mark.asyncio
    async def test_fallback_returns_non_empty_string(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_ai_service import CostAIService

        req = CostEstimateRequest(cpu_cores=4, memory_gb=16, storage_gb=50)
        estimates = self._build_estimates()
        service = CostAIService()

        # Ensure no API key is set for this test
        with patch("app.services.cost_ai_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            suggestion = await service.suggest(req, estimates)

        assert isinstance(suggestion, str)
        assert len(suggestion) > 20

    @pytest.mark.asyncio
    async def test_gemini_path_called_when_key_present(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_ai_service import CostAIService

        req = CostEstimateRequest(cpu_cores=4, memory_gb=16, storage_gb=50)
        estimates = self._build_estimates()
        service = CostAIService()

        with (
            patch("app.services.cost_ai_service.settings") as mock_settings,
            patch.object(
                service,
                "_gemini_suggest",
                new_callable=AsyncMock,
                return_value="Gemini says GCP.",
            ) as mock_gemini,
        ):
            mock_settings.GEMINI_API_KEY = "fake-key-for-test"
            suggestion = await service.suggest(req, estimates)

        mock_gemini.assert_called_once()
        assert suggestion == "Gemini says GCP."

    @pytest.mark.asyncio
    async def test_gemini_failure_falls_back_to_rule_based(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_ai_service import CostAIService

        req = CostEstimateRequest(cpu_cores=4, memory_gb=16, storage_gb=50)
        estimates = self._build_estimates()
        service = CostAIService()

        with (
            patch("app.services.cost_ai_service.settings") as mock_settings,
            patch.object(
                service,
                "_gemini_suggest",
                new_callable=AsyncMock,
                side_effect=RuntimeError("API unavailable"),
            ),
        ):
            mock_settings.GEMINI_API_KEY = "fake-key-for-test"
            # Should NOT raise — falls back to rule-based
            suggestion = await service.suggest(req, estimates)

        assert isinstance(suggestion, str)
        assert len(suggestion) > 0

    @pytest.mark.asyncio
    async def test_empty_estimates_returns_safe_message(self) -> None:
        from app.schemas.cost import CostEstimateRequest
        from app.services.cost_ai_service import CostAIService

        req = CostEstimateRequest(cpu_cores=2, memory_gb=4)
        service = CostAIService()

        with patch("app.services.cost_ai_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            suggestion = await service.suggest(req, [])

        assert "No cost estimates" in suggestion
