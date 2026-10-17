# RealEstate AI 🏢🤖

A modern, production-grade, multi-tenant AI assistant and lead qualification platform engineered for real estate agencies.

---

## 🌟 Key Features

- **Multi-Tenant Architecture**: Complete data isolation across agencies in both PostgreSQL and Qdrant Vector DB.
- **RAG-Powered Property Knowledge**: Ingest property brochures, PDFs, and listings with automatic semantic chunking and vector search.
- **Streaming Conversational Assistant**: Low-latency Server-Sent Events (SSE) chat
- **Automated Lead Qualification**: Real-time extraction of buyer intent, budget, timeline, and contact information.
- **Viewing Appointments & Scheduling**: Integrated booking workflows with calendar sync.
- **Embeddable Chat Widget**: Lightweight, responsive client-side widget ready to drop into any agency website.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Runtime & Package Manager** | Python 3.14+, [uv](https://github.com/astral-sh/uv) |
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Fully Async) + Uvicorn |
| **Database & ORM** | PostgreSQL 16, [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async), `asyncpg`, Alembic |
| **Vector Database** | [Qdrant](https://qdrant.tech/) (Multi-tenant HNSW payload indexing) |
| **Background Tasks** | [ARQ](https://github.com/samuelcolvin/arq) + Redis 7 |
| **AI & Embeddings** | Anthropic Claude, OpenAI, Voyage AI, `sse-starlette` |
| **Logging & Telemetry** | [Structlog](https://www.structlog.org/) (Structured JSON in Prod) |
| **Security** | Argon2-cffi, SHA-256 hashed API keys (`rk_live_...`), PyJWT |

---

## 🏛️ Architecture Overview

The system is structured as a **Domain-Driven Modular Monolith**:

```text
src/app/
├── core/                # Config, logging, middleware, security primitives
├── db/                  # Engine, sessionmaker, declarative base, mixins
├── integrations/        # Qdrant, LLM clients, Embeddings, Calendar, Notifications
├── prompts/             # System prompts and grounding templates
├── workers/             # ARQ background worker tasks and settings
└── modules/             # High-cohesion domain modules
    ├── tenants/         # Agency tenant management & API keys
    ├── documents/       # File upload, storage, and status tracking
    ├── chat/            # Streaming conversations & RAG pipeline
    ├── leads/           # Lead qualification & CRM integration
    ├── bookings/        # Viewing appointments & calendar slots
    └── auth/            # Agency dashboard user authentication & RBAC
```

Each module follows a strict layered pattern:
- `models.py`: SQLAlchemy 2.0 async models (`UUIDPrimaryKeyMixin`, `TimestampMixin`).
- `schemas.py`: Pydantic V2 request/response models.
- `repository.py`: Async database queries strictly scoped by `tenant_id`.
- `service.py`: Business logic, transaction coordination, and domain validations.
- `router.py`: FastAPI endpoints with dependency injection.
- `dependencies.py`: Route-level dependencies (`get_current_tenant`, `get_current_user`).
- `exceptions.py`: Custom domain exceptions mapped to clean HTTP responses.

---

## 🚀 Getting Started

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Fast Python package manager)
- Python 3.14+

### 1. Clone & Environment Setup
```bash
git clone https://github.com/MunawarJamil/realestate_ai.git
cd realestate_ai

# Copy environment template
cp .env.example .env
```

Edit `.env` to configure your API keys and credentials.

### 2. Local Development with Docker
Start PostgreSQL, Redis, Qdrant, API, and Background Worker:
```bash
docker compose -f docker/docker-compose.yml up --build
```

- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qdrant Web Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Running Locally with UV (without Docker for API)
```bash
# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start API server
uv run uvicorn app.main:app --reload --port 8000

# Start ARQ worker in another terminal
uv run arq app.workers.settings.WorkerSettings
```

---

## 🔒 Multi-Tenancy & Security Model

1. **Tenant Isolation**:
   - Every domain entity contains a foreign key to `tenants.id` with `ondelete="CASCADE"`.
   - All repository queries filter explicitly by `tenant_id`.
   - Vector chunks in Qdrant are tagged with a payload keyword index `tenant_id` (`is_tenant=True`), ensuring search queries only return vectors belonging to the caller agency.
2. **API Keys**:
   - Generated with prefix `rk_live_` followed by URL-safe crypto tokens.
   - Only the SHA-256 hash is persisted in the database; raw keys are never stored.
   - Secret comparisons use timing-attack-safe `secrets.compare_digest`.

---

## 🧪 Testing & Code Quality

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src

# Linting & Formatting
uv run ruff check src tests
uv run ruff format src tests
```

---

## 📄 License
Proprietary. All rights reserved.
