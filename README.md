# Infralytix

> **AI-Powered Developer Infrastructure Operating System**

[![CI](https://github.com/Sneharsha001/Infralytix/actions/workflows/ci.yml/badge.svg)](https://github.com/Sneharsha001/Infralytix/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev)
[![MySQL](https://img.shields.io/badge/MySQL-8.4-orange?logo=mysql)](https://mysql.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## What is Infralytix?

Infralytix is a multi-agent infrastructure automation platform that enables developers to:

| Agent | Capability |
|-------|-----------|
| 🔍 **Repo Analyzer** | Detect languages, frameworks, patterns, and tech debt |
| 🐳 **Docker Generator** | Generate production-ready Dockerfiles and Compose files |
| ⚙️ **CI Generator** | Generate GitHub Actions workflows tailored to your stack |
| 🔒 **Security Analyzer** | Scan for vulnerabilities, misconfigurations, and secrets |
| 💰 **Cost Estimator** | Estimate AWS/GCP/Azure infrastructure costs |
| 🏗️ **Architecture Generator** | Generate architecture diagrams from code |
| 📊 **Log Diagnoser** | Diagnose infrastructure logs with AI |
| 📈 **Infrastructure Monitor** | Monitor service health and performance |
| 📄 **Report Generator** | Generate professional PDF infrastructure reports |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│              React 19 + TypeScript + Tailwind            │
└─────────────────────────┬────────────────────────────────┘
                          │ REST API + WebSocket
┌─────────────────────────▼────────────────────────────────┐
│           FastAPI — Versioned API Gateway                │
│         JWT Auth ▸ RBAC ▸ Rate Limiting                  │
├──────────┬───────────┬──────────────┬────────────────────┤
│   Auth   │  Projects │    Agents    │    Reports         │
│ Service  │  Service  │   Service    │    Service         │
├──────────┴───────────┴──────────────┴────────────────────┤
│            Repository Layer (SQLAlchemy ORM)             │
├──────────────────────────────────────────────────────────┤
│                     MySQL 8.4                            │
├──────────────────────────────────────────────────────────┤
│              AI Agent Layer (Google Gemini)              │
└──────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
- **Python 3.12** — Core language
- **FastAPI** — High-performance async REST API framework
- **SQLAlchemy 2.0** — Async ORM with repository pattern
- **Alembic** — Database migration management
- **Pydantic v2** — Data validation and settings management
- **MySQL 8.4** — Primary database
- **JWT + RBAC** — Authentication and authorization

### Frontend
- **React 19** — UI framework
- **TypeScript** — Type-safe JavaScript
- **Tailwind CSS** — Utility-first styling
- **React Router v6** — Client-side routing
- **Axios** — HTTP client with interceptors
- **Vite** — Build tooling

### Infrastructure
- **Docker + Docker Compose** — Containerization
- **GitHub Actions** — CI/CD pipeline
- **AWS** — Cloud deployment (EC2/ECS + RDS + CloudFront)

---

## Getting Started

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | v2+ | Service orchestration |
| Python | 3.12+ | Backend development |
| Node.js | 20+ | Frontend development |
| uv | latest | Python package manager |

### 1. Clone and configure

```bash
git clone https://github.com/Sneharsha001/Infralytix.git
cd infralytix

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your values (especially passwords and SECRET_KEY)
```

### 2. Generate a secure SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

### 3. Start with Docker Compose

```bash
# Production mode
docker compose --env-file .env up -d

# Development mode (with hot reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env up -d
```

### 4. Verify services are running

```bash
# Check all containers
docker compose ps

# Backend health check
curl http://localhost:8000/api/v1/health

# API documentation (development only)
open http://localhost:8000/api/v1/docs
```

### 5. Frontend development (local)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Development Workflow

### Backend

```bash
cd backend

# Install dependencies
uv pip install -e ".[dev]"

# Run development server
uvicorn app.main:app --reload --port 8000

# Run database migrations
alembic upgrade head

# Run tests
pytest tests/ -v --cov=app --cov-report=html

# Lint and format
ruff check app/
ruff format app/
mypy app/
```

### Frontend

```bash
cd frontend

npm run dev          # Development server
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # ESLint
npm run type-check   # TypeScript check
```

---

## Project Structure

```
infralytix/
├── backend/
│   ├── app/
│   │   ├── api/v1/          ← Versioned REST endpoints
│   │   ├── core/            ← Config, logging, security, exceptions
│   │   ├── db/              ← Database session and initialization
│   │   ├── models/          ← SQLAlchemy ORM models
│   │   ├── repositories/    ← Data access layer (Repository Pattern)
│   │   ├── schemas/         ← Pydantic request/response models
│   │   ├── services/        ← Business logic layer
│   │   ├── agents/          ← AI agent implementations
│   │   └── main.py          ← FastAPI application factory
│   ├── alembic/             ← Database migrations
│   ├── tests/               ← Unit and integration tests
│   └── pyproject.toml       ← Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/             ← Axios client + API functions
│   │   ├── components/      ← Reusable UI components
│   │   ├── features/        ← Feature-based modules
│   │   ├── hooks/           ← Custom React hooks
│   │   ├── routes/          ← React Router configuration
│   │   ├── store/           ← State management
│   │   └── types/           ← TypeScript type definitions
│   └── package.json
├── docs/
│   ├── adr/                 ← Architecture Decision Records
│   └── sprint-reviews/      ← Sprint completion documentation
├── .github/workflows/       ← CI/CD pipelines
├── docker-compose.yml       ← Production orchestration
├── docker-compose.dev.yml   ← Development overrides
└── .env.example             ← Environment template
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/health` | GET | Service health check | No |
| `/auth/register` | POST | Register new user | No |
| `/auth/login` | POST | Login and receive JWT | No |
| `/auth/refresh` | POST | Refresh access token | No |
| `/users/me` | GET | Current user profile | Yes |
| `/projects` | GET/POST | List / create projects | Yes |
| `/projects/{id}` | GET/PUT/DELETE | Project operations | Yes |
| `/agents/run` | POST | Trigger an AI agent | Yes |
| `/reports/{id}` | GET | Retrieve agent report | Yes |

> Full API documentation available at `/api/v1/docs` (development mode only)

---

## Sprint Progress

| Sprint | Name | Status |
|--------|------|--------|
| S0 | Project Foundation | ✅ Complete |
| S1 | Backend Core | 🔄 In Progress |
| S2 | Database Layer | ⏳ Pending |
| S3 | Auth System | ⏳ Pending |
| S4 | Project Module | ⏳ Pending |
| S5 | Frontend Foundation | ⏳ Pending |
| S6 | Frontend Dashboard | ⏳ Pending |
| S7 | Agent Framework | ⏳ Pending |
| S8 | AI Agents 1-3 | ⏳ Pending |
| S9 | AI Agents 4-6 | ⏳ Pending |
| S10 | Reports Module | ⏳ Pending |
| S11 | Monitoring | ⏳ Pending |
| S12 | CI/CD Pipeline | ⏳ Pending |
| S13 | AWS Deployment | ⏳ Pending |

---

## Contributing

This project follows a sprint-based development model. See `docs/sprint-reviews/` for detailed sprint documentation.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**Sneha Harsha**  
Platform Engineer · Cloud Engineer · Backend Developer  

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://linkedin.com)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?logo=github)](https://github.com/Sneharsha001)
