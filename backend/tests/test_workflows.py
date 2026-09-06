"""
Tests — Workflow DAG Submission and Validation (POST /api/v1/workflows).

Covers:
  - valid_dag: linear chain, multi-root fork, single task
  - single_node_cycle: task depends on itself
  - multi_node_cycle: A → B → C → A
  - dangling_dependency: depends_on references a non-existent task id
  - empty_task_list: Pydantic rejects an empty list (min_length=1)
  - duplicate_task_id: two tasks share the same id
  - service_unit_tests: WorkflowService.validate_and_build tested directly
  - endpoint_integration: HTTP-level tests via FastAPI TestClient
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.schemas.workflow import (
    TaskCategory,
    WorkflowCreateRequest,
    WorkflowResponse,
    WorkflowTaskRequest,
)
from app.services.workflow_service import WorkflowService, WorkflowValidationError

# =============================================================================
# Helpers
# =============================================================================


def _make_task(
    task_id: str,
    *,
    name: str | None = None,
    category: TaskCategory = TaskCategory.cpu_bound,
    baseline_time_seconds: float = 10.0,
    baseline_vcpu: int = 2,
    baseline_ram_gb: float = 4.0,
    depends_on: list[str] | None = None,
) -> WorkflowTaskRequest:
    """Build a WorkflowTaskRequest with sensible defaults."""
    return WorkflowTaskRequest(
        id=task_id,
        name=name or f"Task {task_id}",
        category=category,
        baseline_time_seconds=baseline_time_seconds,
        baseline_vcpu=baseline_vcpu,
        baseline_ram_gb=baseline_ram_gb,
        depends_on=depends_on or [],
    )


def _make_request(*tasks: WorkflowTaskRequest) -> WorkflowCreateRequest:
    return WorkflowCreateRequest(tasks=list(tasks))


# =============================================================================
# WorkflowService Unit Tests
# =============================================================================


class TestWorkflowServiceValidDAG:
    """WorkflowService accepts semantically correct DAGs."""

    def test_single_task_no_dependencies(self) -> None:
        """A single task with no dependencies is the simplest valid DAG."""
        service = WorkflowService()
        req = _make_request(_make_task("t1"))
        resp = service.validate_and_build(req)

        assert isinstance(resp, WorkflowResponse)
        assert resp.task_count == 1
        assert len(resp.tasks) == 1
        assert resp.tasks[0].id == "t1"
        # Server assigns a uuid
        assert resp.workflow_id is not None

    def test_linear_chain(self) -> None:
        """A → B → C forms a valid acyclic chain."""
        service = WorkflowService()
        req = _make_request(
            _make_task("A"),
            _make_task("B", depends_on=["A"]),
            _make_task("C", depends_on=["B"]),
        )
        resp = service.validate_and_build(req)

        assert resp.task_count == 3
        ids = [t.id for t in resp.tasks]
        assert ids == ["A", "B", "C"]

    def test_multi_root_fork(self) -> None:
        """Two independent roots feeding into a common merge task."""
        service = WorkflowService()
        req = _make_request(
            _make_task("root1"),
            _make_task("root2"),
            _make_task("merge", depends_on=["root1", "root2"]),
        )
        resp = service.validate_and_build(req)

        assert resp.task_count == 3
        merge = next(t for t in resp.tasks if t.id == "merge")
        assert set(merge.depends_on) == {"root1", "root2"}

    def test_all_task_categories_accepted(self) -> None:
        """All four task categories must be accepted without error."""
        service = WorkflowService()
        tasks = [
            _make_task("cpu", category=TaskCategory.cpu_bound),
            _make_task("io", category=TaskCategory.io_bound, depends_on=["cpu"]),
            _make_task("mem", category=TaskCategory.memory_bound, depends_on=["cpu"]),
            _make_task("gpu", category=TaskCategory.gpu_bound, depends_on=["mem"]),
        ]
        resp = service.validate_and_build(_make_request(*tasks))
        assert resp.task_count == 4

    def test_response_preserves_task_fields(self) -> None:
        """WorkflowResponse must echo back all submitted task fields."""
        service = WorkflowService()
        req = _make_request(
            _make_task(
                "t1",
                name="Preprocess",
                category=TaskCategory.io_bound,
                baseline_time_seconds=30.5,
                baseline_vcpu=4,
                baseline_ram_gb=8.0,
            )
        )
        resp = service.validate_and_build(req)
        t = resp.tasks[0]

        assert t.name == "Preprocess"
        assert t.category == TaskCategory.io_bound
        assert t.baseline_time_seconds == 30.5
        assert t.baseline_vcpu == 4
        assert t.baseline_ram_gb == 8.0


class TestWorkflowServiceCycleRejection:
    """WorkflowService rejects any workflow graph that contains a cycle."""

    def test_single_node_self_cycle(self) -> None:
        """A task that depends on itself is a trivial cycle and must be rejected."""
        service = WorkflowService()
        req = _make_request(_make_task("t1", depends_on=["t1"]))

        with pytest.raises(WorkflowValidationError, match="cycle"):
            service.validate_and_build(req)

    def test_two_node_cycle(self) -> None:
        """A ↔ B is a two-node cycle."""
        service = WorkflowService()
        req = _make_request(
            _make_task("A", depends_on=["B"]),
            _make_task("B", depends_on=["A"]),
        )

        with pytest.raises(WorkflowValidationError, match="cycle"):
            service.validate_and_build(req)

    def test_multi_node_cycle(self) -> None:
        """A → B → C → A is a three-node cycle."""
        service = WorkflowService()
        req = _make_request(
            _make_task("A", depends_on=["C"]),
            _make_task("B", depends_on=["A"]),
            _make_task("C", depends_on=["B"]),
        )

        with pytest.raises(WorkflowValidationError, match="cycle"):
            service.validate_and_build(req)

    def test_cycle_in_larger_dag(self) -> None:
        """A cycle embedded in a larger valid-looking graph must still be caught."""
        service = WorkflowService()
        req = _make_request(
            _make_task("root"),                           # valid root
            _make_task("A", depends_on=["root"]),
            _make_task("B", depends_on=["A"]),
            _make_task("C", depends_on=["B"]),            # cycle starts here
            _make_task("leaf", depends_on=["C"]),
        )
        # Introduce a back-edge B → C so that B ← C ← B
        req.tasks[2] = _make_task("B", depends_on=["A", "C"])

        with pytest.raises(WorkflowValidationError, match="cycle"):
            service.validate_and_build(req)


class TestWorkflowServiceDanglingReference:
    """WorkflowService rejects depends_on references to non-existent task ids."""

    def test_single_dangling_reference(self) -> None:
        """depends_on pointing to a task id not in the workflow."""
        service = WorkflowService()
        req = _make_request(
            _make_task("t1"),
            _make_task("t2", depends_on=["DOES_NOT_EXIST"]),
        )

        with pytest.raises(WorkflowValidationError, match="DOES_NOT_EXIST"):
            service.validate_and_build(req)

    def test_multiple_dangling_references(self) -> None:
        """The first encountered dangling reference triggers the error."""
        service = WorkflowService()
        req = _make_request(_make_task("t1", depends_on=["ghost1", "ghost2"]))

        with pytest.raises(WorkflowValidationError, match="ghost1"):
            service.validate_and_build(req)


class TestWorkflowServiceDuplicateId:
    """WorkflowService rejects workflows with duplicate task ids."""

    def test_two_tasks_same_id(self) -> None:
        """Two tasks with identical ids must raise WorkflowValidationError."""
        service = WorkflowService()
        req = _make_request(
            _make_task("duplicate"),
            _make_task("duplicate"),
        )

        with pytest.raises(WorkflowValidationError, match="Duplicate task id"):
            service.validate_and_build(req)


# =============================================================================
# Endpoint Integration Tests
# =============================================================================


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestWorkflowEndpointSuccess:
    """POST /api/v1/workflows returns 201 for valid DAGs."""

    def test_single_task_201(self, client: TestClient) -> None:
        """Minimal valid workflow (one task, no dependencies) → HTTP 201."""
        payload = {
            "tasks": [
                {
                    "id": "t1",
                    "name": "Data Fetch",
                    "category": "io_bound",
                    "baseline_time_seconds": 5.0,
                    "baseline_vcpu": 1,
                    "baseline_ram_gb": 2.0,
                    "depends_on": [],
                }
            ]
        }
        resp = client.post("/api/v1/workflows", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        validated = WorkflowResponse.model_validate(data)

        assert validated.task_count == 1
        assert validated.tasks[0].id == "t1"
        assert validated.workflow_id is not None

    def test_linear_chain_201(self, client: TestClient) -> None:
        """A three-task chain A → B → C is accepted with HTTP 201."""
        payload = {
            "tasks": [
                {
                    "id": "A",
                    "name": "Ingest",
                    "category": "io_bound",
                    "baseline_time_seconds": 10.0,
                    "baseline_vcpu": 2,
                    "baseline_ram_gb": 4.0,
                    "depends_on": [],
                },
                {
                    "id": "B",
                    "name": "Transform",
                    "category": "cpu_bound",
                    "baseline_time_seconds": 60.0,
                    "baseline_vcpu": 8,
                    "baseline_ram_gb": 16.0,
                    "depends_on": ["A"],
                },
                {
                    "id": "C",
                    "name": "Load",
                    "category": "io_bound",
                    "baseline_time_seconds": 5.0,
                    "baseline_vcpu": 2,
                    "baseline_ram_gb": 4.0,
                    "depends_on": ["B"],
                },
            ]
        }
        resp = client.post("/api/v1/workflows", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        assert data["task_count"] == 3
        ids = [t["id"] for t in data["tasks"]]
        assert ids == ["A", "B", "C"]


class TestWorkflowEndpointCycleRejection:
    """POST /api/v1/workflows returns 422 for cyclic graphs."""

    def test_self_cycle_422(self, client: TestClient) -> None:
        """A task that depends on itself returns 422."""
        payload = {
            "tasks": [
                {
                    "id": "t1",
                    "name": "Self-referential",
                    "category": "cpu_bound",
                    "baseline_time_seconds": 5.0,
                    "baseline_vcpu": 1,
                    "baseline_ram_gb": 1.0,
                    "depends_on": ["t1"],
                }
            ]
        }
        resp = client.post("/api/v1/workflows", json=payload)

        assert resp.status_code == 422
        body = resp.json()
        assert "cycle" in body["error"]["message"].lower()
        assert body["error"]["code"] == "WORKFLOW_VALIDATION_ERROR"

    def test_multi_node_cycle_422(self, client: TestClient) -> None:
        """A → B → C → A returns 422."""
        payload = {
            "tasks": [
                {
                    "id": "A",
                    "name": "A",
                    "category": "cpu_bound",
                    "baseline_time_seconds": 1.0,
                    "baseline_vcpu": 1,
                    "baseline_ram_gb": 1.0,
                    "depends_on": ["C"],
                },
                {
                    "id": "B",
                    "name": "B",
                    "category": "cpu_bound",
                    "baseline_time_seconds": 1.0,
                    "baseline_vcpu": 1,
                    "baseline_ram_gb": 1.0,
                    "depends_on": ["A"],
                },
                {
                    "id": "C",
                    "name": "C",
                    "category": "cpu_bound",
                    "baseline_time_seconds": 1.0,
                    "baseline_vcpu": 1,
                    "baseline_ram_gb": 1.0,
                    "depends_on": ["B"],
                },
            ]
        }
        resp = client.post("/api/v1/workflows", json=payload)

        assert resp.status_code == 422
        body = resp.json()
        assert "cycle" in body["error"]["message"].lower()


class TestWorkflowEndpointDanglingReference:
    """POST /api/v1/workflows returns 422 when depends_on references a missing task id."""

    def test_dangling_reference_422(self, client: TestClient) -> None:
        """depends_on pointing to a non-existent task id returns 422."""
        payload = {
            "tasks": [
                {
                    "id": "t1",
                    "name": "Task 1",
                    "category": "cpu_bound",
                    "baseline_time_seconds": 5.0,
                    "baseline_vcpu": 2,
                    "baseline_ram_gb": 4.0,
                    "depends_on": ["nonexistent_task_id"],
                }
            ]
        }
        resp = client.post("/api/v1/workflows", json=payload)

        assert resp.status_code == 422
        body = resp.json()
        assert "nonexistent_task_id" in body["error"]["message"]
        assert body["error"]["code"] == "WORKFLOW_VALIDATION_ERROR"


class TestWorkflowEndpointPydanticValidation:
    """POST /api/v1/workflows returns 422 for Pydantic-level constraint violations."""

    def test_empty_task_list_422(self, client: TestClient) -> None:
        """An empty tasks list violates min_length=1 and returns 422."""
        resp = client.post("/api/v1/workflows", json={"tasks": []})
        assert resp.status_code == 422

    def test_missing_tasks_field_422(self, client: TestClient) -> None:
        """A request body with no 'tasks' key returns 422."""
        resp = client.post("/api/v1/workflows", json={})
        assert resp.status_code == 422

    def test_invalid_category_422(self, client: TestClient) -> None:
        """An unrecognised category enum value returns 422."""
        payload = {
            "tasks": [
                {
                    "id": "t1",
                    "name": "Bad Category",
                    "category": "quantum_bound",  # not a valid TaskCategory
                    "baseline_time_seconds": 5.0,
                    "baseline_vcpu": 2,
                    "baseline_ram_gb": 4.0,
                    "depends_on": [],
                }
            ]
        }
        resp = client.post("/api/v1/workflows", json=payload)
        assert resp.status_code == 422

    def test_negative_baseline_time_422(self, client: TestClient) -> None:
        """baseline_time_seconds must be > 0; negative value returns 422."""
        payload = {
            "tasks": [
                {
                    "id": "t1",
                    "name": "Negative Time",
                    "category": "cpu_bound",
                    "baseline_time_seconds": -5.0,
                    "baseline_vcpu": 2,
                    "baseline_ram_gb": 4.0,
                    "depends_on": [],
                }
            ]
        }
        resp = client.post("/api/v1/workflows", json=payload)
        assert resp.status_code == 422

    def test_duplicate_task_id_422(self, client: TestClient) -> None:
        """Two tasks with the same id return 422 (WorkflowValidationError)."""
        task = {
            "id": "same",
            "name": "Duplicate",
            "category": "cpu_bound",
            "baseline_time_seconds": 1.0,
            "baseline_vcpu": 1,
            "baseline_ram_gb": 1.0,
            "depends_on": [],
        }
        resp = client.post("/api/v1/workflows", json={"tasks": [task, task]})
        assert resp.status_code == 422
        body = resp.json()
        assert "Duplicate task id" in body["error"]["message"]
