# ADR-001 — Technology Stack Selection

**Status**: Accepted  
**Date**: 2025-07-15  
**Author**: Sneha Harsha  
**Context**: Infralytix Sprint 0

---

## Context

Infralytix is a portfolio project targeting Cloud Engineer, Platform Engineer, and Backend Developer roles.
The technology stack must:

1. Reflect production-level engineering decisions
2. Be aligned with industry standards for infrastructure tooling
3. Demonstrate modern Python backend and React frontend skills
4. Support future AI/ML integration

---

## Decision

### Backend: Python 3.12 + FastAPI

**Chosen over**: Django REST Framework, Flask, Node.js/Express

**Rationale**:
- FastAPI is the standard for modern Python APIs in ML/AI tooling (matches career target)
- Native async support aligns with I/O-bound AI agent operations
- Pydantic v2 integration provides compile-time safety similar to TypeScript
- Auto-generated OpenAPI documentation aids portfolio presentation
- Uvicorn ASGI server is production-grade and supports WebSockets (needed for Sprint 7+)

### Database: MySQL 8.4

**Chosen over**: PostgreSQL, MongoDB, SQLite

**Rationale**:
- Specified in project requirements
- Widely used in enterprise environments (strong portfolio signal)
- MySQL 8 supports window functions, CTEs, JSON columns (not "legacy MySQL")
- RDS MySQL is cheaper than RDS PostgreSQL for equivalent workloads (relevant for Sprint 13 AWS deployment)

**Trade-off**: PostgreSQL has better full-text search and JSONB performance. If requirements change, SQLAlchemy's abstraction layer makes migration feasible with Alembic.

### ORM: SQLAlchemy 2.0 + Alembic

**Chosen over**: Tortoise ORM, raw SQL, Prisma

**Rationale**:
- SQLAlchemy 2.0 is the industry standard; widely expected in senior Python roles
- Repository pattern works naturally with SQLAlchemy sessions
- Alembic migrations are version-controlled and reversible
- Both async (aiomysql) and sync (pymysql) drivers available — needed for Alembic vs FastAPI

### Package Manager: uv

**Chosen over**: pip, Poetry, PDM

**Rationale**:
- 10-100x faster than pip
- Drop-in replacement — no new file format to learn
- Single binary, no separate `pip` + `venv` tooling
- Gaining rapid industry adoption (Rust-based, cross-platform)

### Frontend: React 19 + TypeScript + Tailwind CSS + Vite

**Chosen over**: Vue, Svelte, Angular, Next.js

**Rationale**:
- React 19 is the most in-demand frontend framework
- TypeScript eliminates runtime type errors (portfolio quality signal)
- Tailwind CSS enables rapid, consistent UI development without CSS bloat
- Vite is significantly faster than Webpack/CRA for development feedback loop
- No SSR needed for an infrastructure dashboard (React SPA is sufficient)

### Authentication: JWT (HttpOnly Cookies)

**Chosen over**: Session-based auth, OAuth-only, localStorage JWT

**Rationale**:
- JWT is stateless — no session store needed (scales horizontally)
- HttpOnly cookies prevent XSS attacks (more secure than localStorage)
- Short-lived access tokens + long-lived refresh tokens follows best practice
- RBAC middleware supports multi-role authorization without external dependencies

### Containerization: Docker + Docker Compose

**Rationale**:
- Reproducible environments across development, CI, and production
- docker-compose.yml is the standard for multi-service development setups
- Multi-stage Dockerfiles minimize production image size and attack surface
- Direct path to Kubernetes deployment (Sprint 13+)

### CI/CD: GitHub Actions

**Chosen over**: Jenkins, GitLab CI, CircleCI

**Rationale**:
- Zero infrastructure cost for public repositories
- Native integration with GitHub (required for PR-based workflows)
- Marketplace actions for uv, Docker Buildx, Codecov
- Familiar to hiring teams reviewing portfolio

---

## Consequences

**Positive**:
- Each technology choice directly maps to a job description requirement
- The stack is modern enough to be impressive but stable enough to be production-ready
- All components are open-source and free for portfolio use

**Negative / Trade-offs**:
- FastAPI + SQLAlchemy async has more complexity than synchronous alternatives
- MySQL vs PostgreSQL may require justification in interviews
- JWT refresh token rotation adds implementation complexity (Sprint 3)

---

## Review

This decision will be reviewed before Sprint 13 (AWS Deployment) to validate that the stack supports horizontal scaling and managed cloud services.
