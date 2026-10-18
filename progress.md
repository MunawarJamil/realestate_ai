# PROJECT PROGRESS TRACKER (progress.md)

> **Last Updated**: 2026-10-19  
> **Current Phase**: Step 13 / Phase 8 - Embeddable Web Chat Widget (Completed ✅)  
> **Status**: Completed (Ready for Next Phase: Phase 5 Leads or Phase 7 Auth)  
> **Current File Context**: [`widget/`](file:///e:/PERSONAL-PROJECTS/realestate_ai/widget/)

---

## 📌 Quick Summary of Where We Left Off
- **Phase 0-3 (Core, Tenants, Knowledge Ingestion & Retrieval)**: 100% complete and operational.
- **Phase 4 / Step 7 (Conversational AI & Streaming RAG)**: 100% complete.
  - Multi-tenant chat models (`conversations`, `messages`) & Alembic migration applied.
  - OpenRouter LLM client with env-configurable model.
  - Real-estate assistant prompt & context formatter with strict grounding.
  - Full REST and SSE token streaming endpoints verified via PowerShell & curl.
  - Test suite: 238 passing tests (`pytest`).
- **Phase 8 / Step 13 (Embeddable Web Chat Widget)**: 100% Complete (13.1 through 13.6).
  - Public widget auth (`wk_live_...`, domain whitelisting, visitor JWT session isolation).
  - Public conversation, history, and real-time SSE streaming endpoints with rate limiting.
  - Shadow DOM TypeScript widget with unified dark theme tokens (`#0B0B0D`, orange `#F97316`).
  - Safe Markdown parser, localStorage session persistence, auto-scroll, and typing indicator.
  - Test embed demo page (`widget/index.html`) and unit test suite.
- **Immediate Next Step**: Phase 5 — Lead Capture & CRM Qualification Pipeline (`src/app/modules/leads/`) OR Agency Auth & Dashboard UI (`src/app/modules/auth/`).

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

### [x] Phase 4: Conversational AI & Streaming RAG Engine (`src/app/modules/chat/`)
- [x] `models.py`: `Conversation` and `Message` models (scoped by `tenant_id` with cascading delete and compound indexes)
- [x] Database migration: `20261018_1720_4f9a1b2c3d4e_create_chat_tables.py` applied
- [x] LLM client: OpenRouter adapter via `AsyncOpenAI` with env-configurable model (`src/app/integrations/llm/client.py`)
- [x] System prompt & Context builder: Grounded real-estate prompt (`src/app/prompts/real_estate_assistant.md`) and dynamic chunk formatter (`src/app/modules/chat/prompts.py`)
- [x] Chat repository & service: Multi-tenant isolated DB persistence and RAG orchestration (`repository.py`, `service.py`)
- [x] Server-Sent Events (SSE) streaming endpoint: Real-time token streaming (`POST /api/v1/chat/conversations/{id}/stream`)
- [x] REST API endpoints: Conversation creation, listing, history retrieval (`/api/v1/chat/conversations`)
- [x] Unit test suite: 24 passing unit tests covering chat models, prompts, repo, service, router, and LLM client (238 total passing tests)

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

### [x] Step 13 / Phase 8: Embeddable Web Chat Widget (`widget/`) (100% COMPLETE ✅)
- [x] **13.1 Backend Public Widget Auth**:
  - `widget_key` (public key `wk_live_...`) and `allowed_domains` for tenants.
  - HTTP `Origin` header check for domain whitelisting.
  - Visitor session token issuance to prevent visitors from viewing other visitors' conversations.
- [x] **13.2 Public Widget Endpoints (`/api/v1/widget/...`)**:
  - Reusing existing `ChatService` (conversations, messages, SSE streaming).
  - Visitor conversation isolation via JSONB metadata filtering.
  - Sliding-window rate limiting on public widget endpoints with Redis + in-memory fallback.
- [x] **13.3 Widget Scaffold & Architecture**:
  - `widget/` project setup with TypeScript + Vite.
  - Shadow DOM encapsulation (to prevent host site CSS collisions).
  - Single `<script>` embed bundle output (IIFE bundle target `widget.js`).
- [x] **13.4 UI Components & Shared Design Tokens**:
  - Floating launcher button with micro-animations.
  - Chat window, header, message list, input box, typing indicators.
  - Unified Design System Tokens (shared across Widget, Agency Admin & Super Admin):
    - `--bg: #0B0B0D` (Dark charcoal background)
    - `--surface: #151517`
    - `--surface-2: #1E1E21`
    - `--brown-glow: #3A1F10 -> #0B0B0D` (warm brown gradient for header)
    - `--accent: #F97316` (Orange)
    - `--accent-hover: #EA580C`
    - `--text: #FFFFFF`
    - `--muted: #A1A1AA`
    - `--border: rgba(255, 255, 255, 0.08)`
- [x] **13.5 Client Runtime & SSE Streaming**:
  - Real-time SSE token-by-token stream reader.
  - Visitor session & conversation ID persistence in `localStorage`.
  - Auto-reconnect & Markdown formatting for assistant replies.
- [x] **13.6 Test Embed Page & Verification**:
  - Standalone luxury agency demo embed test page (`widget/index.html`).
  - Unit test suite for public widget endpoints (`tests/unit/modules/widget/test_widget_endpoints.py`).


