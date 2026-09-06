"""
Tests — Workflow Evaluator (app/services/workflow_evaluator.py).

All tests are pure unit tests: no I/O, no network, no database.

Hand-computed reference values
--------------------------------
Diamond DAG: A -> B, A -> C, B -> D, C -> D  (all cpu_bound, 2x baseline vCPU)

    instance: 4 vCPU, 16 GB RAM, $1.00/hr, no GPU

    baseline tasks (all at 2 vCPU):
        A: 100 s   B: 200 s   C: 50 s   D: 80 s

    vcpu_ratio = 4 / 2 = 2.0, speedup = min(2.0, 16.0) = 2.0
    scaled:
        A: 100 / 2 = 50 s
        B: 200 / 2 = 100 s
        C:  50 / 2 =  25 s
        D:  80 / 2 =  40 s

    Critical paths:
        A → B → D : 50 + 100 + 40 = 190 s   ← LONGEST
        A → C → D : 50 +  25 + 40 = 115 s

    Makespan = 190 s

    Individual costs (at $1.00/hr):
        A: (50/3600) * 1.00  = 0.013889 USD
        B: (100/3600) * 1.00 = 0.027778 USD
        C: (25/3600) * 1.00  = 0.006944 USD
        D: (40/3600) * 1.00  = 0.011111 USD

    total_cost = (50 + 100 + 25 + 40) / 3600 * 1.00
               = 215 / 3600
               = 0.059722 USD
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.schemas.workflow import TaskCategory, WorkflowResponse, WorkflowTaskResponse
from app.schemas.workflow_evaluation import InstanceSpec, TaskEvaluation, WorkflowEvaluation
from app.services.workflow_evaluator import (
    IO_MAX_SPEEDUP,
    IO_VCPU_EXPONENT,
    MAX_CPU_SPEEDUP,
    MAX_RAM_SPEEDUP,
    WorkflowEvaluationError,
    compute_makespan,
    evaluate_workflow,
    scale_task_time,
)

# =============================================================================
# Helpers
# =============================================================================


def _task(
    task_id: str,
    *,
    category: TaskCategory = TaskCategory.cpu_bound,
    baseline_time: float = 100.0,
    baseline_vcpu: int = 2,
    baseline_ram_gb: float = 4.0,
    depends_on: list[str] | None = None,
) -> WorkflowTaskResponse:
    return WorkflowTaskResponse(
        id=task_id,
        name=f"Task {task_id}",
        category=category,
        baseline_time_seconds=baseline_time,
        baseline_vcpu=baseline_vcpu,
        baseline_ram_gb=baseline_ram_gb,
        depends_on=depends_on or [],
    )


def _instance(
    vcpu: int = 4,
    ram_gb: float = 16.0,
    hourly_price: float = 1.0,
    has_gpu: bool = False,
) -> InstanceSpec:
    return InstanceSpec(
        vcpu=vcpu, ram_gb=ram_gb, hourly_price_usd=hourly_price, has_gpu=has_gpu
    )


def _workflow(*tasks: WorkflowTaskResponse) -> WorkflowResponse:
    return WorkflowResponse(
        workflow_id=uuid.uuid4(),
        task_count=len(tasks),
        tasks=list(tasks),
    )


# =============================================================================
# scale_task_time — Unit Tests
# =============================================================================


class TestScaleTaskTimeCpuBound:
    def test_exact_speedup_at_double_vcpus(self) -> None:
        task = _task("t", category=TaskCategory.cpu_bound, baseline_time=100.0, baseline_vcpu=2)
        inst = _instance(vcpu=4)
        result = scale_task_time(task, inst)
        # vcpu_ratio = 4/2 = 2.0, speedup = 2.0 → 100 / 2 = 50
        assert result == pytest.approx(50.0)

    def test_sub_baseline_vcpu_is_slower(self) -> None:
        """Fewer vCPUs than baseline → scaled time is longer than baseline."""
        task = _task("t", category=TaskCategory.cpu_bound, baseline_time=100.0, baseline_vcpu=8)
        inst = _instance(vcpu=2)
        result = scale_task_time(task, inst)
        # vcpu_ratio = 2/8 = 0.25 → scaled = 100/0.25 = 400 s
        assert result == pytest.approx(400.0)

    def test_cpu_speedup_capped_at_max(self) -> None:
        """Speedup is capped at MAX_CPU_SPEEDUP regardless of vCPU ratio."""
        task = _task("t", category=TaskCategory.cpu_bound, baseline_time=1000.0, baseline_vcpu=1)
        inst = _instance(vcpu=1000)  # ratio = 1000, way above cap
        result = scale_task_time(task, inst)
        assert result == pytest.approx(1000.0 / MAX_CPU_SPEEDUP)

    def test_same_vcpu_no_scaling(self) -> None:
        """Identical vcpu count → baseline time returned unchanged."""
        task = _task("t", category=TaskCategory.cpu_bound, baseline_time=60.0, baseline_vcpu=4)
        inst = _instance(vcpu=4)
        result = scale_task_time(task, inst)
        assert result == pytest.approx(60.0)


class TestScaleTaskTimeIoBound:
    def test_io_speedup_is_sublinear(self) -> None:
        """IO tasks scale weakly — speedup < vCPU ratio."""
        task = _task("t", category=TaskCategory.io_bound, baseline_time=100.0, baseline_vcpu=2)
        inst = _instance(vcpu=4)
        vcpu_ratio = 4 / 2
        expected_speedup = min(vcpu_ratio**IO_VCPU_EXPONENT, IO_MAX_SPEEDUP)
        expected = 100.0 / expected_speedup
        result = scale_task_time(task, inst)
        assert result == pytest.approx(expected)

    def test_io_speedup_capped(self) -> None:
        """IO speedup is capped at IO_MAX_SPEEDUP even with enormous vCPU ratio."""
        task = _task("t", category=TaskCategory.io_bound, baseline_time=200.0, baseline_vcpu=1)
        inst = _instance(vcpu=500)
        result = scale_task_time(task, inst)
        assert result == pytest.approx(200.0 / IO_MAX_SPEEDUP)

    def test_io_slower_with_fewer_vcpus(self) -> None:
        task = _task("t", category=TaskCategory.io_bound, baseline_time=100.0, baseline_vcpu=8)
        inst = _instance(vcpu=2)
        vcpu_ratio = 2 / 8
        expected_speedup = min(vcpu_ratio**IO_VCPU_EXPONENT, IO_MAX_SPEEDUP)
        expected = 100.0 / expected_speedup
        result = scale_task_time(task, inst)
        assert result == pytest.approx(expected)


class TestScaleTaskTimeMemoryBound:
    def test_exact_speedup_at_double_ram(self) -> None:
        task = _task(
            "t",
            category=TaskCategory.memory_bound,
            baseline_time=100.0,
            baseline_ram_gb=8.0,
        )
        inst = _instance(ram_gb=16.0)
        result = scale_task_time(task, inst)
        # ram_ratio = 16/8 = 2.0 → scaled = 100/2 = 50
        assert result == pytest.approx(50.0)

    def test_less_ram_is_slower(self) -> None:
        task = _task(
            "t",
            category=TaskCategory.memory_bound,
            baseline_time=100.0,
            baseline_ram_gb=32.0,
        )
        inst = _instance(ram_gb=8.0)
        # ram_ratio = 8/32 = 0.25 → scaled = 100/0.25 = 400
        result = scale_task_time(task, inst)
        assert result == pytest.approx(400.0)

    def test_memory_speedup_capped(self) -> None:
        task = _task(
            "t",
            category=TaskCategory.memory_bound,
            baseline_time=500.0,
            baseline_ram_gb=1.0,
        )
        inst = _instance(ram_gb=10000.0)
        result = scale_task_time(task, inst)
        assert result == pytest.approx(500.0 / MAX_RAM_SPEEDUP)


class TestScaleTaskTimeGpuBound:
    def test_gpu_task_incompatible_without_gpu(self) -> None:
        task = _task("t", category=TaskCategory.gpu_bound, baseline_time=300.0)
        inst = _instance(has_gpu=False)
        result = scale_task_time(task, inst)
        assert result is None

    def test_gpu_task_compatible_with_gpu_instance(self) -> None:
        task = _task("t", category=TaskCategory.gpu_bound, baseline_time=300.0)
        inst = _instance(has_gpu=True)
        result = scale_task_time(task, inst)
        # No further GPU-specific scaling — returns baseline unchanged
        assert result == pytest.approx(300.0)


# =============================================================================
# compute_makespan — Unit Tests
# =============================================================================


class TestComputeMakespan:
    def test_single_task(self) -> None:
        tasks = [_task("A")]
        result = compute_makespan(tasks, {"A": 120.0})
        assert result == pytest.approx(120.0)

    def test_linear_chain_makespan_is_sum(self) -> None:
        """A → B → C: makespan = 50 + 100 + 40 = 190 s."""
        tasks = [
            _task("A"),
            _task("B", depends_on=["A"]),
            _task("C", depends_on=["B"]),
        ]
        result = compute_makespan(tasks, {"A": 50.0, "B": 100.0, "C": 40.0})
        assert result == pytest.approx(190.0)

    def test_parallel_tasks_makespan_is_longest(self) -> None:
        """A with two parallel successors B and C (no common sink):
           makespan = A + max(B, C) when B and C have no deps each other."""
        tasks = [
            _task("A"),
            _task("B", depends_on=["A"]),
            _task("C", depends_on=["A"]),
        ]
        result = compute_makespan(tasks, {"A": 50.0, "B": 30.0, "C": 80.0})
        # A → B: 50 + 30 = 80
        # A → C: 50 + 80 = 130  ← critical path
        assert result == pytest.approx(130.0)

    def test_diamond_dag_critical_path(self) -> None:
        """
        Diamond: A → B, A → C, B → D, C → D
        All cpu_bound at 2 vCPU baseline, candidate = 4 vCPU (speedup = 2×)

        Scaled times:
            A = 100/2 = 50 s
            B = 200/2 = 100 s
            C =  50/2 =  25 s
            D =  80/2 =  40 s

        Critical paths:
            A → B → D : 50 + 100 + 40 = 190 s  ← LONGEST
            A → C → D : 50 +  25 + 40 = 115 s

        Expected makespan = 190 s
        """
        tasks = [
            _task("A", baseline_time=100.0, baseline_vcpu=2),
            _task("B", baseline_time=200.0, baseline_vcpu=2, depends_on=["A"]),
            _task("C", baseline_time=50.0, baseline_vcpu=2, depends_on=["A"]),
            _task("D", baseline_time=80.0, baseline_vcpu=2, depends_on=["B", "C"]),
        ]
        # Manually provide scaled times (2× speedup)
        scaled: dict[str, float] = {"A": 50.0, "B": 100.0, "C": 25.0, "D": 40.0}
        result = compute_makespan(tasks, scaled)
        assert result == pytest.approx(190.0), (
            f"Expected critical path A→B→D = 190 s, got {result} s"
        )

    def test_no_edges_makespan_is_max_task(self) -> None:
        """Independent tasks (no edges) run in parallel; makespan = longest task."""
        tasks = [_task("X"), _task("Y"), _task("Z")]
        result = compute_makespan(tasks, {"X": 30.0, "Y": 90.0, "Z": 45.0})
        assert result == pytest.approx(90.0)

    def test_empty_scaled_times_returns_zero(self) -> None:
        tasks = [_task("A")]
        result = compute_makespan(tasks, {})
        assert result == 0.0


# =============================================================================
# evaluate_workflow — Integration (pure) Tests
# =============================================================================


class TestEvaluateWorkflowDiamondDAG:
    """
    Primary verification: hand-computed diamond DAG.

    Diamond: A → B, A → C, B → D, C → D
    All cpu_bound at 2 vCPU / 4 GB baseline.
    Instance: 4 vCPU, 16 GB, $1.00/hr, no GPU.

    Scaled times (×2 speedup):
        A = 50 s, B = 100 s, C = 25 s, D = 40 s

    Critical path A → B → D = 190 s (makespan)

    Total cost = (50 + 100 + 25 + 40) / 3600 × $1.00
               = 215 / 3600 ≈ $0.059722
    """

    def test_makespan_equals_critical_path(self) -> None:
        wf = _workflow(
            _task("A", baseline_time=100.0, baseline_vcpu=2, baseline_ram_gb=4.0),
            _task("B", baseline_time=200.0, baseline_vcpu=2, baseline_ram_gb=4.0, depends_on=["A"]),
            _task("C", baseline_time=50.0, baseline_vcpu=2, baseline_ram_gb=4.0, depends_on=["A"]),
            _task(
                "D",
                baseline_time=80.0,
                baseline_vcpu=2,
                baseline_ram_gb=4.0,
                depends_on=["B", "C"],
            ),
        )
        inst = _instance(vcpu=4, ram_gb=16.0, hourly_price=1.0)
        result = evaluate_workflow(wf, inst)

        assert isinstance(result, WorkflowEvaluation)
        assert result.makespan_seconds == pytest.approx(190.0, rel=1e-4)

    def test_makespan_is_not_sum_of_all_tasks(self) -> None:
        """Sanity: makespan must be < sum of all scaled times (190 < 215)."""
        wf = _workflow(
            _task("A", baseline_time=100.0, baseline_vcpu=2),
            _task("B", baseline_time=200.0, baseline_vcpu=2, depends_on=["A"]),
            _task("C", baseline_time=50.0, baseline_vcpu=2, depends_on=["A"]),
            _task("D", baseline_time=80.0, baseline_vcpu=2, depends_on=["B", "C"]),
        )
        inst = _instance(vcpu=4)
        result = evaluate_workflow(wf, inst)

        scaled_sum = 50.0 + 100.0 + 25.0 + 40.0  # 215 s
        assert result.makespan_seconds < scaled_sum

    def test_total_cost_includes_all_tasks(self) -> None:
        """Total cost = sum of individual task costs (not just critical path)."""
        wf = _workflow(
            _task("A", baseline_time=100.0, baseline_vcpu=2),
            _task("B", baseline_time=200.0, baseline_vcpu=2, depends_on=["A"]),
            _task("C", baseline_time=50.0, baseline_vcpu=2, depends_on=["A"]),
            _task("D", baseline_time=80.0, baseline_vcpu=2, depends_on=["B", "C"]),
        )
        inst = _instance(vcpu=4, hourly_price=1.0)
        result = evaluate_workflow(wf, inst)

        expected_total = (50.0 + 100.0 + 25.0 + 40.0) / 3600.0 * 1.0
        assert result.total_cost_usd == pytest.approx(expected_total, rel=1e-4)

    def test_task_evaluation_count_matches_workflow(self) -> None:
        wf = _workflow(
            _task("A", baseline_time=100.0, baseline_vcpu=2),
            _task("B", baseline_time=200.0, baseline_vcpu=2, depends_on=["A"]),
            _task("C", baseline_time=50.0, baseline_vcpu=2, depends_on=["A"]),
            _task("D", baseline_time=80.0, baseline_vcpu=2, depends_on=["B", "C"]),
        )
        inst = _instance(vcpu=4)
        result = evaluate_workflow(wf, inst)

        assert len(result.task_evaluations) == 4
        task_ids = {e.task_id for e in result.task_evaluations}
        assert task_ids == {"A", "B", "C", "D"}


class TestEvaluateWorkflowGpuIncompatibility:
    def test_single_gpu_task_incompatible_on_cpu_instance(self) -> None:
        wf = _workflow(_task("g1", category=TaskCategory.gpu_bound))
        inst = _instance(has_gpu=False)

        with pytest.raises(WorkflowEvaluationError, match="gpu_bound"):
            evaluate_workflow(wf, inst)

    def test_mixed_gpu_and_cpu_tasks_partial_eval(self) -> None:
        """GPU task is incompatible; CPU tasks still produce a valid evaluation."""
        wf = _workflow(
            _task("cpu", category=TaskCategory.cpu_bound, baseline_time=100.0, baseline_vcpu=2),
            _task("gpu", category=TaskCategory.gpu_bound, baseline_time=300.0),
        )
        inst = _instance(has_gpu=False)
        result = evaluate_workflow(wf, inst)

        assert "gpu" in result.incompatible_tasks
        assert "cpu" not in result.incompatible_tasks

        gpu_eval = next(e for e in result.task_evaluations if e.task_id == "gpu")
        assert gpu_eval.scaled_time_seconds is None
        assert gpu_eval.cost_usd == 0.0

    def test_all_gpu_tasks_raise_error(self) -> None:
        wf = _workflow(
            _task("g1", category=TaskCategory.gpu_bound),
            _task("g2", category=TaskCategory.gpu_bound, depends_on=["g1"]),
        )
        inst = _instance(has_gpu=False)
        with pytest.raises(WorkflowEvaluationError):
            evaluate_workflow(wf, inst)

    def test_gpu_task_compatible_on_gpu_instance(self) -> None:
        wf = _workflow(_task("g1", category=TaskCategory.gpu_bound, baseline_time=300.0))
        inst = _instance(has_gpu=True)
        result = evaluate_workflow(wf, inst)

        assert result.incompatible_tasks == []
        g_eval = result.task_evaluations[0]
        assert g_eval.scaled_time_seconds == pytest.approx(300.0)
        assert result.makespan_seconds == pytest.approx(300.0)


class TestEvaluateWorkflowPricingAccuracy:
    def test_cost_scales_with_hourly_price(self) -> None:
        wf = _workflow(_task("t", baseline_time=3600.0, baseline_vcpu=2))  # 1 hour at baseline
        inst_1usd = _instance(vcpu=2, hourly_price=1.0)
        inst_2usd = _instance(vcpu=2, hourly_price=2.0)

        result_1 = evaluate_workflow(wf, inst_1usd)
        result_2 = evaluate_workflow(wf, inst_2usd)

        # Same vcpu count → no scaling; 1 hour × rate
        assert result_1.total_cost_usd == pytest.approx(1.0, rel=1e-4)
        assert result_2.total_cost_usd == pytest.approx(2.0, rel=1e-4)

    def test_more_vcpus_reduce_cost_for_cpu_bound(self) -> None:
        """Faster execution at same price → lower cost."""
        wf = _workflow(
            _task("t", category=TaskCategory.cpu_bound, baseline_time=7200.0, baseline_vcpu=2)
        )
        inst_slow = _instance(vcpu=2, hourly_price=1.0)   # no speedup
        inst_fast = _instance(vcpu=4, hourly_price=1.0)   # 2× speedup

        result_slow = evaluate_workflow(wf, inst_slow)
        result_fast = evaluate_workflow(wf, inst_fast)

        assert result_slow.total_cost_usd > result_fast.total_cost_usd


class TestEvaluateWorkflowCategoryVariety:
    def test_io_bound_single_task(self) -> None:
        """io_bound scaling produces a valid positive makespan."""
        wf = _workflow(
            _task("t", category=TaskCategory.io_bound, baseline_time=100.0, baseline_vcpu=2)
        )
        inst = _instance(vcpu=8)
        result = evaluate_workflow(wf, inst)

        assert result.makespan_seconds > 0
        # io_bound speedup capped at IO_MAX_SPEEDUP → makespan >= 100/IO_MAX_SPEEDUP
        assert result.makespan_seconds >= 100.0 / IO_MAX_SPEEDUP - 1e-9

    def test_memory_bound_single_task(self) -> None:
        wf = _workflow(
            _task(
                "t",
                category=TaskCategory.memory_bound,
                baseline_time=100.0,
                baseline_ram_gb=8.0,
            )
        )
        inst = _instance(ram_gb=16.0)
        result = evaluate_workflow(wf, inst)
        # ram_ratio = 2 → scaled = 50 s
        assert result.makespan_seconds == pytest.approx(50.0, rel=1e-4)

    def test_mixed_categories_linear_chain(self) -> None:
        """Linear chain with different categories: makespan = sum of scaled times."""
        wf = _workflow(
            _task("cpu", category=TaskCategory.cpu_bound, baseline_time=100.0, baseline_vcpu=2),
            _task(
                "io",
                category=TaskCategory.io_bound,
                baseline_time=100.0,
                baseline_vcpu=2,
                depends_on=["cpu"],
            ),
            _task(
                "mem",
                category=TaskCategory.memory_bound,
                baseline_time=100.0,
                baseline_ram_gb=4.0,
                depends_on=["io"],
            ),
        )
        # instance: 4 vCPU, 8 GB RAM, $1/hr
        inst = _instance(vcpu=4, ram_gb=8.0, hourly_price=1.0)

        cpu_speedup = min(4 / 2, MAX_CPU_SPEEDUP)              # 2.0
        io_speedup = min((4 / 2) ** IO_VCPU_EXPONENT, IO_MAX_SPEEDUP)
        ram_speedup = min(8.0 / 4.0, MAX_RAM_SPEEDUP)          # 2.0

        expected_makespan = 100 / cpu_speedup + 100 / io_speedup + 100 / ram_speedup
        result = evaluate_workflow(wf, inst)

        assert result.makespan_seconds == pytest.approx(expected_makespan, rel=1e-4)


class TestEvaluateWorkflowEdgeCases:
    def test_single_task_no_dependencies(self) -> None:
        wf = _workflow(_task("solo", baseline_time=60.0, baseline_vcpu=2))
        inst = _instance(vcpu=2)
        result = evaluate_workflow(wf, inst)

        assert result.makespan_seconds == pytest.approx(60.0)
        assert result.incompatible_tasks == []
        assert len(result.task_evaluations) == 1

    def test_independent_parallel_tasks_makespan_is_longest(self) -> None:
        """Three independent tasks with different scaled times."""
        wf = _workflow(
            _task("x", baseline_time=100.0, baseline_vcpu=2),
            _task("y", baseline_time=600.0, baseline_vcpu=2),  # longest
            _task("z", baseline_time=200.0, baseline_vcpu=2),
        )
        inst = _instance(vcpu=2)  # no speedup → scaled = baseline
        result = evaluate_workflow(wf, inst)
        assert result.makespan_seconds == pytest.approx(600.0)

    def test_workflow_evaluation_is_a_pydantic_model(self) -> None:
        wf = _workflow(_task("t", baseline_time=100.0, baseline_vcpu=2))
        inst = _instance(vcpu=4)
        result = evaluate_workflow(wf, inst)

        assert isinstance(result, WorkflowEvaluation)
        dumped: dict[str, Any] = result.model_dump()
        assert "makespan_seconds" in dumped
        assert "total_cost_usd" in dumped
        assert "task_evaluations" in dumped
        assert "incompatible_tasks" in dumped

    def test_task_evaluation_is_a_pydantic_model(self) -> None:
        wf = _workflow(_task("t", baseline_time=100.0, baseline_vcpu=2))
        inst = _instance(vcpu=4)
        result = evaluate_workflow(wf, inst)

        te = result.task_evaluations[0]
        assert isinstance(te, TaskEvaluation)
        assert te.task_id == "t"
        assert te.scaled_time_seconds is not None and te.scaled_time_seconds > 0
        assert te.cost_usd >= 0
