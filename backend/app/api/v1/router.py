"""
Infralytix — API v1 Router.

This module is the single assembly point for all v1 endpoints.
Adding a new feature = import its router here and include it.

Current routers:
    /health     — Service liveness and readiness checks

Upcoming routers (added in future sprints):
    /auth       — Registration, login, token refresh
    /users      — User profile management
    /projects   — Project CRUD
    /agents     — AI agent invocation
    /reports    — Report retrieval
"""

from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router

# All v1 routes are assembled here.
# The /api/v1 prefix is applied by main.py when including this router.
v1_router = APIRouter()

v1_router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

# Future routers will be added below:
# v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# v1_router.include_router(users_router, prefix="/users", tags=["Users"])
# v1_router.include_router(projects_router, prefix="/projects", tags=["Projects"])
# v1_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
# v1_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
