# Functional Requirement 11: Workflow DAG Submission and Optimization

**Traces to:** This feature was implemented and tested ahead of formal specification. It was discovered during a documentation/code audit and is being documented retroactively.

| ID | Requirement | Priority |
| :--- | :--- | :--- |
| **FR11.1** | System shall accept a workflow definition as a DAG of tasks with resource profiles and dependency edges, and validate it for structural correctness (uniqueness, referential integrity, acyclicity).<br><br>*(Evidence: `app/services/workflow_service.py`, `tests/test_workflows.py`, `POST /api/v1/workflows` - 22 passing tests)* | P1 |
| **FR11.2** | System shall estimate execution time and cost for each task on a candidate cloud instance using category-aware scaling from a user-supplied baseline.<br><br>*(Evidence: `workflow_evaluator.py`, `tests/test_workflow_evaluator.py`)* | P1 |
| **FR11.3** | System shall compute total workflow cost and time (via critical-path makespan, not simple summation) for a given instance assignment.<br><br>*(Evidence: `workflow_evaluator.py`, `tests/test_workflow_evaluator.py`, `POST /api/v1/workflows/optimize`)* | P1 |
| **FR11.4** | System shall sweep candidate instances across AWS, Azure, and GCP concurrently and return the Pareto-optimal set of (cost, time) outcomes.<br><br>*(Evidence: `app/services/workflow_optimizer_service.py`, `tests/test_workflow_optimizer.py` - 81 passing tests)* | P1 |
| **FR11.5** | System shall label the Pareto-optimal set with Fastest, Cheapest, and Best-balance recommendations, and generate a plain-language AI summary of the tradeoff.<br><br>*(Evidence: `app/services/workflow_optimizer_service.py`, `src/features/workflows/` components: DagPreview, ParetoScatterChart, AiSummaryCard, routed at `/workflows`)* | P2 |
