# PROJECT PROGRESS TRACKER (progress.md)

> **Last Updated**: 2026-10-17  
> **Current Phase**: Phase 2 - Document Management & Ingestion Pipeline  
> **Status**: In Progress  
> **Current File Context**: [`src/app/modules/documents/`](file:///e:/PERSONAL-PROJECTS/realestate_ai/src/app/modules/documents/)

---

## 📌 Quick Summary of Where We Left Off
- **Tenants Module (`src/app/modules/tenants/`)**: 100% complete with models, repo, service, router, and `X-API-Key` auth.
- **Documents Module (`src/app/modules/documents/`)**:
  - `enums.py`: Done (`DocumentStatus`: pending, processing, ready, failed).
  - `models.py`: Done (`Document` model with multi-tenant FK, SHA256 checksum deduplication, JSONB metadata, non-native enum).
  - **Immediate Next Step**: Build `schemas.py`, `repository.py`, and `service.py` for document uploads & storage handling.

---

## 🗺️ Roadmap & Phase Breakdown

### [x] Phase 0: Project Setup & Core Infrastructure
- [x] UV package management setup (`pyproject.toml`) with Python 3.14
- [x] Docker & Docker Compose setup (FastAPI, ARQ Worker, Postgres 16, Redis 7, Qdrant)
- [x] Core Config (`src/app/core/config.py`) using `pydantic-settings`
- [x] Structured Logging (`src/app/core/logging.py`) with Structlog
- [x] Security Utilities (`src/app/core/security.py`) for API key generation & hashing
- [x] Database Foundation (`src/app/db/base.py`, `session.py`) with async engine & sessionmaker
- [x] Qdrant Client & Multi-Tenant Collection Init (`src/app/integrations/qdrant/`)
- [x] FastAPI App Factory & Lifespan (`src/app/main.py`)
- [x] Alembic Async Migration Config (`migrations/env.py`)

---

### [x] Phase 1: Multi-Tenancy & Agency Management (`src/app/modules/tenants/`)
- [x] `models.py`: `Tenant` model with slug and hashed API keys (`rk_live_...`)
- [x] `schemas.py`: Pydantic V2 schemas (`TenantCreate`, `TenantCreated`, `TenantRead`)
- [x] `repository.py`: Async queries for tenant lifecycle and authentication
- [x] `service.py`: Creation, raw key generation, and timing-safe authentication
- [x] `router.py`: Admin endpoints (`POST /api/v1/tenants`, `GET /api/v1/tenants/me`)
- [x] `dependencies.py`: `get_current_tenant` dependency for API authentication
- [x] `exceptions.py`: Custom tenant exceptions

---

### [ ] Phase 2: Knowledge Base & Document Management (`src/app/modules/knowledge/`) (IN PROGRESS 🟡)
- [x] Consolidate `modules/documents` into `modules/knowledge`
- [x] `enums.py`: `DocumentStatus` (pending, processing, ready, failed)
- [x] `models.py`: `KnowledgeDocument` model with tenant isolation, checksum deduplication, and JSONB metadata
- [x] Database Migration: `20261017_0818_2e5fb9c2154e_create_knowledge_documents_table.py` generated and applied
- [ ] `schemas.py`: Pydantic schemas for document upload, read, and list
- [ ] `repository.py`: Document CRUD operations scoped strictly by `tenant_id`
- [ ] Storage Service: Local file storage / S3 adapter for raw PDF storage
- [ ] `service.py`: Upload validation (MIME, size, checksum), DB persistence, ARQ dispatch
- [ ] `router.py`: Upload and management endpoints (`/api/v1/knowledge`)

---

### [ ] Phase 3: Background Worker & RAG Ingestion Pipeline (IN PROGRESS 🟡)
- [x] `EmbeddingProvider` Protocol definition (`src/app/integrations/embeddings/base.py`)
- [x] OpenRouter async `EmbeddingClient` with batching, bounded concurrency, and exponential backoff (`src/app/integrations/embeddings/client.py`)
- [x] Embedding exceptions (`EmbeddingError`, `EmbeddingDimensionError`)
- [x] FastAPI lifespan integration (`init_embedding_client`, `close_embedding_client`)
- [x] Unit & integration test suite (21 passing tests in `tests/unit` & `tests/integration`)
- [ ] Text extraction service (PDF parsing via `pypdf`, Markdown parser)
- [ ] Semantic & token-aware chunking engine
- [ ] Qdrant chunk upsert worker task (with strict `tenant_id` and `document_id` payload tags)
- [ ] ARQ worker tasks (`src/app/workers/tasks.py`) & lifecycle handling

---

### [ ] Phase 4: Conversational AI & Streaming RAG Engine (`src/app/modules/chat/`)
- [ ] `models.py`: `Conversation` and `Message` models (scoped by `tenant_id`)
- [ ] Semantic search service (Qdrant similarity search with tenant payload filter)
- [ ] Prompt construction & System Prompt management (`src/app/prompts/real_estate_assistant.md`)
- [ ] LLM integration adapter (`src/app/integrations/llm/anthropic.py` / `openai.py`)
- [ ] Server-Sent Events (SSE) streaming endpoint (`/api/v1/chat/stream`)
- [ ] Automatic lead detail extractor (budget, bedrooms, timeline, contact info)

---

### [ ] Phase 5: Lead Capture & Qualification Pipeline (`src/app/modules/leads/`)
- [ ] `models.py`: `Lead` model with qualification score, budget, intent, status
- [ ] `schemas.py`, `repository.py`, `service.py`, `router.py`
- [ ] Automated CRM scoring & status progression (New -> Qualified -> Contacted)
- [ ] Real-time notification dispatch (Email / Webhook to real estate agent)

---

### [ ] Phase 6: Viewing Bookings & Scheduling (`src/app/modules/bookings/`)
- [ ] `models.py`: `Booking` model linked to `Lead`, `Tenant`, and optional property
- [ ] Availability slot engine
- [ ] Calendar integration (`src/app/integrations/calendar/`)
- [ ] Confirmation and reminder notifications

---

### [ ] Phase 7: Agency Auth & Dashboard API (`src/app/modules/auth/`)
- [ ] `User` model with roles (Agency Admin, Agent)
- [ ] Argon2 password hashing & JWT token issue/refresh
- [ ] Protected agency dashboard routes

---

### [ ] Phase 8: Embeddable Web Chat Widget (`widget/`)
- [ ] Lightweight Vanilla JS/TS embeddable bundle
- [ ] Streaming UI, Markdown rendering, auto-reconnect
- [ ] Lead capture form integration
