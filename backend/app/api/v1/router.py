"""
Infralytix — API v1 Router.

This module is the single assembly point for all v1 endpoints.
Adding a new feature = import its router here and include it.

Current routers:
    /health       — Service liveness and readiness checks
    /auth         — Registration, login, token refresh
    /projects     — Project CRUD and repository upload
    /projects     — AI agent invocation (analyze, analysis)
    /cost         — Multi-cloud cost comparison with AI suggestion
    /workflows    — Workflow DAG submission and validation
"""

from fastapi import APIRouter

from app.api.v1.endpoints.agents import router as agents_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cost import router as cost_router
from app.api.v1.endpoints.cost_comparison import router as cost_comparison_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.workflows import router as workflows_router

# All v1 routes are assembled here.
# The /api/v1 prefix is applied by main.py when including this router.
v1_router = APIRouter()

v1_router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

v1_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

v1_router.include_router(
    projects_router,
    prefix="/projects",
    tags=["Projects"],
)

v1_router.include_router(
    agents_router,
    prefix="/projects",
    tags=["AI Agents"],
)

v1_router.include_router(
    cost_router,
    prefix="/cost",
    tags=["Cost Comparison"],
)

v1_router.include_router(
    cost_comparison_router,
    prefix="/cost-comparison",
    tags=["Cost Comparison"],
)

v1_router.include_router(
    workflows_router,
    prefix="/workflows",
    tags=["Workflows"],
)
