# PROJECT PROGRESS TRACKER (progress.md)

> **Last Updated**: 2026-10-20  
> **Current Phase**: Phase 12 (Socket.IO + LangGraph HITL + Verification Completed ✅) ➔ Next: Phase 13 (CRM Leads Pipeline & Webhook Integrations)  
> **Status**: Phase 12 100% Tested & Verified via Automated PowerShell Suite  
> **Current File Context**: [`src/app/modules/chat/`](file:///e:/PERSONAL-PROJECTS/realestate_ai/src/app/modules/chat/) & [`scratch/test_lifecycle.ps1`](file:///C:/Users/HP/.gemini/antigravity-ide/brain/f6d7e5db-9cc7-4a63-be34-6cb9a0b753d7/scratch/test_lifecycle.ps1)

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
- **Phase 9 / Step 14 & 15 (Dual-Role Dashboard UI)**: 100% Complete ✅:
  - [x] **14.1 Frontend Scaffold & Design Tokens**: React 19 + Vite + Tailwind CSS with unified dark luxury palette (`#0B0B0D`, `#151517`, `#F97316`).
  - [x] **14.2 Dual-Portal Shell & Routing**: TanStack Router code-based tree for `/platform/*` and `/app/*`.
  - [x] **14.3 Super Admin Login**: Discrete access portal with MFA indicators and dark luxury styling.
  - [x] **14.4 Super Admin Overview**: 4 high-value KPI cards, microservices health, and live tenant traffic.
  - [x] **14.5 Tenants Management**: Search, filter, status suspend/activate toggling, and "Provision New Agency" modal.
  - [x] **14.6 System & AI Gateway (`/platform/system`)**: Emergency AI Traffic Circuit Breaker toggle, microservices telemetry, and sliding-window rate limit policy inspector.
  - [x] **14.7 Platform Audit & Security Logs (`/platform/audit`)**: Filterable chronological administrative audit trail with actor IP and event badges.
  - [x] **14.8 Tenant Configuration Drawer**: On-the-fly allowed domains whitelist editing and instant zero-downtime key rotation.
  - [x] **15.1 Agency Data Contracts & Mock State**: `types/agency.ts` and `mock/agencyData.ts` (Conversations, Leads, KnowledgeDocs).
  - [x] **15.2 Agency Overview & Split Conversations Inbox**:
    - `AgencyDashboardPage.tsx`: 4 high-value KPIs (Today's inquiries, Hot CRM leads, Indexed docs, Grounding rate), hot leads alert table, live embed card.
    - `AgencyConversationsPage.tsx`: Split 2-pane inbox with visitor cards, full transcript reader, grounded RAG citation badges, visitor CRM metadata, and agent reply action.
  - [x] **15.3 CRM Qualified Leads Pipeline (`/app/leads`)**:
    - `AgencyLeadsPage.tsx`: Interactive pipeline table with search, status filtering, AI score thresholds (Hot $\ge 85$, Warm $70-84$), status dropdown updater, manual lead entry modal, and CSV export.
  - [x] **15.5 Agency Widget Customization & Embed Settings (`/app/settings`)**:
    - `AgencySettingsPage.tsx`: Interactive 1:1 scale live widget preview with dynamic accent color selection, custom welcome greeting, quick inquiry prompts, and whitelisted origin script tag.
  - [x] **15.6 Responsive, Spacing & Table Layout Overhaul**:
    - Mobile slide-out drawer sidebar with hamburger button for `<lg` devices.
    - Full horizontal table scrolling with single-line rows (`whitespace-nowrap`) preventing broken multi-word cells across all data tables (Knowledge, Leads, Tenants, Audit).
    - Vertically stacked clean contact info (Name, Phone below with icon, Email below with icon) in CRM leads table.
    - Conversation 2-pane inbox UX polish: reduced sidebar width to compact `w-64/w-72`, single-line truncated message previews, and separated floating bottom with clear margins.
  - [x] **15.7 Dual Theme System (Dark Mode + Porcelain `#FFFCF4` Light Mode)**:
    - Persistent theme context (`ThemeContext.tsx`) syncing to `localStorage` and `<html>` classes (`light` / `dark`).
    - Interactive animated `<ThemeToggle />` pill button placed in both Agency Admin and Super Admin top headers.
    - Complete luxury Porcelain palette (`#FFFCF4` canvas, `#FAF5E8` sidebar, `#FFFFFF` crisp cards, warm stone borders `#E8E2D5`, and deep stone typography).
- **Phase 7 & 8: Authentication, RBAC & Multi-Tenant Live Integration (COMPLETED ✅)**:
  - [x] **Step 8.1 & 8.2: Dual-Role Authentication & RBAC**:
    - PostgreSQL `users` table created with `role` (`super_admin`, `agency_admin`, `agent`), foreign key `tenant_id` to `tenants(id)`, and hashed passwords via `argon2`.
    - Endpoints: `POST /api/v1/auth/login` (agency JWT with `aud="agency"`) and `POST /api/v1/auth/platform/login` (super admin JWT with `aud="platform"`).
    - Hardened route security: Platform routes reject non-super_admin tokens; agency routes strictly resolve `tenant_id` from the authenticated user token.
  - [x] **Super Admin Agency Onboarding with Admin Credentials**:
    - Super Admin can enter Agency Name, Allowed Domains, and provision initial Admin Email & Password directly in the "Provision New Agency" modal.
    - One-click "Copy Complete Onboarding Pack" generates client handover bundle (Portal URL, Email, Password, API Key, Widget Key, and Embed Snippet).
  - [x] **Zero-Cross-Agency Leakage & Clean State Enforcement**:
    - Removed all hardcoded mock data (`Apex Luxury`) from Agency Dashboard, Leads, Conversations, and Settings.
    - When a newly onboarded agency logs in, they see a completely clean workspace tailored exclusively to their tenant.
    - Added comprehensive empty states and a "Workspace Modules & Tab Directory" roadmap indicating the exact purpose and mechanics of each tab (`Conversations`, `Leads & CRM`, `Knowledge Base`, `Widget & Settings`).
    - Frontend bundle validated (`npm run build`) with zero TypeScript errors.
  - [x] **Step 7.4: Agency Admin Knowledge Base Live Wiring (`/app/knowledge`)**:
    - Connected `AgencyLoginPage.tsx` to live backend tenant verification via `GET /api/v1/tenants/me`.
    - Connected `AgencyLayout.tsx` to dynamic agency branding and session logout.
    - Wired `AgencyKnowledgePage.tsx` to real backend endpoints: `GET /api/v1/knowledge/documents`, multipart file upload `POST /api/v1/knowledge/documents`, document deletion `DELETE /api/v1/knowledge/documents/{id}`.
    - Integrated automatic background polling for in-flight document chunking & vectorization.
  - [x] **Step 7.5: Agency Live Conversations & Assistant SSE Streaming (`/app/conversations`)**:
    - Wired `AgencyConversationsPage.tsx` to `GET /api/v1/chat/conversations` and message history `GET /api/v1/chat/conversations/{id}/messages`.
    - Integrated real-time SSE token-by-token streaming reader via `POST /api/v1/chat/conversations/{id}/stream`.
    - Added instant thread provisioning via `POST /api/v1/chat/conversations`.
- **Phase 12: Real-Time Human Handoff & Hybrid WebSocket Gateway (IN PROGRESS 🟡)**:
  - [x] **Step 12b.1: Database Enums, Models & Alembic Migration**:
    - Defined `ConversationStatus` (`ai`, `handoff_requested`, `human_active`, `resolved`) and `SenderType` (`visitor`, `ai`, `agent`, `system`) in `src/app/modules/chat/enums.py`.
    - Added `status` (default `'ai'`, indexed), `assigned_agent_id` (FK to `users.id`), and `assigned_agent` relationship to `Conversation` model with composite index `ix_conversations_tenant_status`.
    - Added `sender_type` (default `'visitor'`, indexed) and `agent_id` (FK to `users.id`) to `Message` model.
    - Updated `ConversationRead`, `MessageRead`, and added `ConversationStatusUpdateRequest` and `ConversationSummaryResponse` in `schemas.py`.
    - Updated `ChatRepository` and `ChatService` with backward-compatible defaults, status filtering, and `update_conversation_status`.
    - Applied Alembic migration `4cecc086a386` to PostgreSQL.
  - [x] **Step 12b.2: Distributed Redis Pub/Sub Connection Hub & Event Bus (`# 12b HITL`)**:
    - Strongly typed Pydantic event envelope `WSEvent` with `WSEventType` (token, message, status_change, handoff_request, agent_claimed, agent_released, typing, ping, pong) in `src/app/modules/chat/events.py`.
    - `RedisPubSubManager` in `src/app/modules/chat/redis_pubsub.py` providing multi-process Redis channel pub/sub isolation (`tenant:{id}:conv:{conv_id}` and `tenant:{id}:agent_alerts`).
    - `ConnectionManager` in `src/app/modules/chat/connection_manager.py` with multi-socket client registration, Redis listener background tasks, and thread-safe broadcast dispatch.
  - [x] **Step 12b.3: FastAPI Dual WebSocket Gateways (`# 12b HITL`)**:
    - Multi-lingual intent detector (English, Arabic, Urdu/Hindi Roman) and guardrail reply generator in `src/app/modules/chat/handoff.py`.
    - `/api/v1/chat/ws/agent`: Agency broker/agent endpoint (Agency JWT auth, claim, release, live agent reply).
    - `/api/v1/chat/ws/{conversation_id}`: Visitor widget endpoint (Visitor token auth, live AI stream dispatch, handoff detection).
    - Starlette routing precedence configured (static `/agent` before dynamic `/{conversation_id}`).
  - [x] **Step 12b.4: Agent Claim, Release & Resolve REST Endpoints (`# 12b HITL`)**:
    - `POST /api/v1/chat/conversations/{conversation_id}/claim`: Authenticates agency agent, assigns `assigned_agent_id`, sets status to `human_active`, adds system audit message, and broadcasts `STATUS_CHANGE` over Redis Pub/Sub.
    - `POST /api/v1/chat/conversations/{conversation_id}/release`: Sets status to `ai`, clears `assigned_agent_id`, creates audit message, and broadcasts update.
    - `POST /api/v1/chat/conversations/{conversation_id}/resolve`: Closes conversation with `resolved` status and notifies realtime listeners.
    - Added eager reload & refresh pattern to prevent async SQLAlchemy greenlet expiry on serialization.
  - [x] **Step 12b.5: Real-time AI Handover Summary Generator (`# 12b HITL`)**:
    - `build_summary_messages()` prompt builder in `src/app/modules/chat/prompts.py` extracting structured JSON summary (intent, budget, preferred location).
    - `GET /api/v1/chat/conversations/{conversation_id}/summary` in `router.py` & `service.py`: Generates instant 2-second executive brief for live brokers stepping into a visitor thread.
    - Automated integration test `test_hitl_endpoints.py` passing 100%.
  - [x] **Step 12b.6: Embeddable Widget WebSocket Shift (`# 12b HITL`)**:
    - Created `WidgetWebSocketClient` in `widget/src/ws.ts` with auto-reconnection, 25s heartbeat pings, and strongly-typed frame dispatching.
    - Extended `types.ts` with `sender_type` (`visitor`, `ai`, `agent`, `system`) and `status` (`ai`, `handoff_requested`, `human_active`, `resolved`).
    - Added styles in `styles.ts` for `.re-msg-agent` (distinctive broker blue badge) and `.re-msg-system` (pill event announcements).
    - Upgraded `main.ts` runtime to initiate WebSocket on conversation start, handle live AI token streams and incoming broker messages over a single connection, and fallback gracefully to HTTP SSE if WebSocket is blocked.
    - Updated dynamic header status indicator (AI Assistant vs Connecting vs Live Advisor Connected vs Resolved).
  - [x] **Step 12b.7: Dashboard Live Agent Inbox UI (`AgencyConversationsPage.tsx`) (`# 12b HITL`)**:
    - Created `AgentWebSocketClient` in `dashboard/src/api/agentWs.ts` listening to tenant-wide Redis handoff alerts (`/api/v1/chat/ws/agent`), live visitor messages, and presence state.
    - Updated `dashboard/src/types/agency.ts` and `dashboard/src/api/client.ts` with `claimConversation`, `releaseConversation`, `resolveConversation`, and `getConversationSummary`.
    - Added status filter pills (All | 🚨 Handoffs | 👤 Live Advisor | 🤖 AI | Resolved).
    - Added dismissable alert banner when any visitor triggers human handoff in real-time.
    - Added 1-click **"Claim Conversation"**, **"Release to AI"**, and **"Mark Resolved"** action buttons.
    - Added interactive **"⚡ AI Brief"** executive summary drawer rendering stated intent, budget, and location.
    - Added live agent WebSocket reply input delivering broker messages directly to the visitor widget in real-time.
    - Dashboard build passed (`npm run build` -> `485.9 kB`, 0 TS errors).
- **Phase 12 (Real-Time Human Handoff & Hybrid WebSocket Gateway) Status**: 100% COMPLETE ✅!







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

### [x] Phase 2: Knowledge Base & Document Management (`src/app/modules/knowledge/`) (100% COMPLETE ✅)
- [x] Consolidate `modules/documents` into `modules/knowledge`
- [x] `enums.py`: `DocumentStatus` (pending, processing, ready, failed)
- [x] `models.py`: `KnowledgeDocument` model with tenant isolation, checksum deduplication, and JSONB metadata
- [x] Database Migration applied
- [x] `schemas.py`: Pydantic schemas for document upload, read, and list
- [x] `repository.py`: Document CRUD operations scoped strictly by `tenant_id`
- [x] Storage Service: Local file storage / S3 adapter for raw PDF storage (`storage.py`)
- [x] `service.py`: Upload validation (MIME, size, checksum), DB persistence, ARQ dispatch
- [x] `router.py`: Upload and management endpoints (`/api/v1/knowledge`)

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

### [ ] Phase 7: Dashboard API & Backend Live Integration (IN PROGRESS 🟡)
- [x] **7.1 Backend Super Admin Tenants API**: `GET /api/v1/tenants`, `PATCH /api/v1/tenants/{id}`, repo queries, service methods.
- [x] **7.2 Dynamic Auth Store & Production API Client**: Zustand `useAuthStore` with localStorage persistence, `apiClient` with typed `ApiError` & SSE stream reader.
- [x] **7.3 Super Admin Portal Live Wiring (`/platform/*`)**: Real tenant fetching, instant provisioning modal with secret key display, status toggling, allowed origins whitelist.
- [x] **7.4 Agency Knowledge Base Live Wiring (`/app/knowledge`)**: Real PDF/doc upload, document listing, ingestion status polling, and Qdrant semantic search tester.
- [x] **7.5 Agency Live Conversations & Streaming (`/app/conversations`)**: Chat inbox, conversation history, real-time SSE assistant streaming.
- [ ] **7.6 End-to-End Verification**: Complete smoke tests and validation.

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

---

### [x] Phase 9 / Step 14: Dual-Role Dashboard UI (`dashboard/`) (COMPLETED ✅)
- [x] **Dual Entrypoint & Architecture Strategy**:
  - Alag entry points, same codebase:
    - `/login` & `/app/*` for Agency Admin.
    - `/platform/login` & `/platform/*` for Super/Platform Admin (isolated discrete gateway).
- [x] **Frontend Tech Stack Setup**:
  - React 19 + Vite in `dashboard/` (Port 5174).
  - Tailwind CSS with unified dark palette tokens (`#0B0B0D`, `#151517`, `#F97316`, warm glow).
  - TanStack Router code-based routing tree with type safety.
- [x] **V1 Implementation (Static / Mock UI)**:
  - Super-Admin layout & dedicated sidebar (`/platform/*`).
  - Lean Platform Overview with 4 high-value KPI cards and core services health.
  - Agency / Tenant management table with search, status toggling, credentials preview, and "Provision Agency" modal.
  - Agency-Admin (`/app/*`) layout & portal overview scaffold ready for CRM and Knowledge modules.

---

### [x] Phase 8: Multi-Tenant Auth, RBAC & Gateway Separation (COMPLETED ✅)
- [x] **8.1 Core Security & Password Infrastructure**:
  - Argon2id password hashing and constant-time verification (`hash_password`, `verify_password`) via `argon2-cffi`.
  - Audience-segregated JWT issuance & decoding (`create_user_tokens`, `decode_user_token`) with explicit audience claims (`aud="platform"` vs `aud="agency"`).
- [x] **8.2 Database Architecture & Migrations**:
  - `UserRole` enum: `super_admin`, `agency_admin`, `agent`.
  - `User` SQLAlchemy model with nullable `tenant_id` (cascading delete on tenant removal).
  - Multi-tenant unique constraints: partial unique index on `email` where `tenant_id IS NULL` for platform super admins; composite unique constraint `uq_users_tenant_email` on `(tenant_id, email)` for agency members.
  - Alembic migration `20261019_1500_6b7c8d9e0f1a_create_users_table.py` executed and verified in PostgreSQL.
- [x] **8.3 Service Layer & Cross-Role Enforcement**:
  - `UserRepository` providing tenant-scoped and platform-level queries.
  - `AuthService` with discrete login pathways:
    - Agency portal login (`authenticate_agency_user`): verifies tenant slug/credentials and strictly rejects `super_admin` attempts with `403 Forbidden`.
    - Platform gateway login (`authenticate_platform_user`): verifies root super admin credentials and strictly rejects agency accounts with `403 Forbidden`.
  - Refresh token rotation and user lifecycle management (`create_user`, `list_agency_users`).
- [x] **8.4 FastAPI Endpoints & RBAC Security Guards**:
  - `POST /api/v1/auth/login`: Agency login issuing `aud="agency"` access & refresh tokens.
  - `POST /api/v1/auth/platform/login`: Super Admin login issuing `aud="platform"` access & refresh tokens.
  - `POST /api/v1/auth/refresh`: Refresh token rotation with audience validation.
  - `GET /api/v1/auth/me`: Authenticated user profile reader.
  - `POST /api/v1/auth/users` & `GET /api/v1/auth/users`: Tenant-scoped user creation and directory listing (accessible by `agency_admin`).
  - Guards: `require_platform_admin`, `require_agency_user`, `require_agency_admin`.
  - Dual-auth support on `/api/v1/tenants`: Accepts either `X-Admin-Key` header or Platform Super Admin Bearer JWT.
- [x] **8.5 Seeding & Live Verification**:
  - Created and executed `scripts/seed_auth_users.py`:
    - Platform Super Admin: `admin@platform.internal` / `SuperAdminPassword123!`
    - Demo Agency Admin: `admin@prestige.com` / `AgencyAdminPassword123!`
    - Demo Agency Agent: `agent@prestige.com` / `AgentPassword123!`
  - Verified live cross-role rejection in both directions via PowerShell/curl.
- [x] **8.6 Frontend Dashboard Integration**:
  - Zustand auth store (`useAuthStore.ts`) extended with `platformToken`, `agencyToken`, `platformUser`, and `agencyUser`.
  - Type-safe `apiClient` (`client.ts`) extended with `apiClient.auth.*` and dynamic JWT Bearer header injection with API-key fallbacks.
  - Upgraded `PlatformLoginPage.tsx` with JWT credentials login and Super Admin badge.
  - Upgraded `AgencyLoginPage.tsx` with work email/password login, tenant slug detection, and RBAC support.
  - Integrated active user profile display and role badges in `SuperAdminLayout.tsx` and `AgencyLayout.tsx`.
  - Verified `tsc -b && vite build` passed with zero errors.
- [x] **Phase 12c: Socket.IO Real-Time Gateway (Visitor <-> Agency Live Communication)**:
  - Backend: `python-socketio` AsyncServer mounted as ASGI wrapper in `main.py`.
  - Multi-tenant room isolation: `conv_{id}` for active conversation channels and `tenant_{id}_agents` for agency-wide alerts.
  - Full-duplex Socket.IO client in embeddable widget (`widget/src/socket.ts`).
  - Real-time `AgentSocketClient` in agency dashboard (`dashboard/src/api/agentSocket.ts`).
  - Verified two-way live messaging between website widget visitor and agency broker without page reloads.
- [x] **Phase 12d: LangGraph Human-in-the-Loop (HITL) State Machine Orchestration**:
  - Schema (`graph_state.py`): Typed `AgentState` schema with append-only messages reducer (`add_messages`) and merged metadata reducer (`merge_dicts`).
  - Graph Engine (`hitl_graph.py`): Intent router node, RAG agent node, human review node, and conditional routing based on handoff detection and AI failure thresholds.
  - Runtime Lifecycle (`graph_runtime.py`): Eager startup compilation (`init_graph()`), Postgres checkpointing pool support with fallback to `MemorySaver`, thread isolation (`configurable: {thread_id: tenant_id:conv_id}`), and per-conversation distributed Redis locking.
  - Gateway Integration (`socketio_server.py`): Visitor messages trigger LangGraph turns via `run_visitor_turn`; broker replies trigger `sync_agent_message` resetting inactivity timers. Metadata-based visitor isolation via `conv.metadata_["visitor_id"]`.
  - App Lifespan (`main.py`): Wire `await init_graph()` and `await shutdown_graph()` into ASGI application startup and shutdown.
- [x] **Phase 12e: Legacy Real-Time Code Cleanup & Consolidation**:
  - Deleted obsolete native WebSocket endpoints and managers: `widget/src/ws.ts`, `src/app/modules/chat/ws_router.py`, `src/app/modules/chat/connection_manager.py`, and `src/app/modules/chat/events.py` (~834 lines removed).
  - Unmounted dead `ws_router` from `main.py`.
  - Refactored `ChatService` REST actions (`claim_conversation`, `release_conversation`, `resolve_conversation`, `send_message`) to broadcast directly via `sio.emit`.
  - Cleaned `redis_pubsub.py` to serve purely as Redis client connection lifecycle manager.
  - Verified widget build (`70.08 kB`), dashboard build (`526 kB`), and backend ASGI app loading with 0 errors.
- [x] **Phase 12f: Automated End-to-End PowerShell Verification of AI Assistant & HITL Lifecycle**:
  - Validated Step 1: Visitor Session Init (`POST /api/v1/widget/session` with `X-Widget-Key`) -> Verified visitor JWT token and tenant context.
  - Validated Step 2: Conversation Creation (`POST /api/v1/widget/conversations`) -> Initial state `ai`.
  - Validated Step 3: Grounded AI RAG Retrieval (`POST /api/v1/widget/conversations/{id}/messages`) -> Retrieved Qdrant vectors for `AP-DEMO-103, Dabouq Family Villa` with zero hallucinations and accurate pricing (JOD 285,000).
  - Validated Step 4: Human Broker Handoff Guardrail -> Visitor requested human agent, triggering handoff acknowledgment.
  - Validated Step 5: Agency Broker Authentication (`POST /api/v1/auth/login`) -> Verified JWT access token generation with `aud="agency"`.
  - Validated Step 6: Agent Claim Conversation (`POST /api/v1/chat/conversations/{id}/claim`) -> Successfully transitioned status to `human_active` and assigned to agent.
  - Validated Step 7: AI Silence Enforcement -> Confirmed AI remains silent while broker is actively managing the thread.
  - Validated Step 8: AI Handover Executive Brief (`GET /api/v1/chat/conversations/{id}/summary`) -> LLM extracted structured intent (`Luxury Villa`), location (`Dabouq, Amman`), and budget (`JOD 285,000`).
  - Validated Step 9: Agent Resolution (`POST /api/v1/chat/conversations/{id}/resolve`) -> Transitioned conversation to `resolved`.
  - Validated Step 10: Multi-Tenant Conversation Listing (`GET /api/v1/chat/conversations`) -> Verified state persistence and listing in tenant workspace.



