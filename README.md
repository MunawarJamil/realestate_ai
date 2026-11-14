# 🏢 PropChat | Multi-Tenant Real Estate AI Platform

> A production-grade, multi-tenant AI conversational platform for real estate agencies — featuring grounded RAG, LangGraph tool-calling, real-time human broker handoff, and an embeddable website widget.

---

## ⚡ What is PropChat?

PropChat transforms real estate agency websites into 24/7 lead-generation engines:

1. **Visitors** chat with an AI assistant that answers questions from agency brochures, searches listings, and calculates mortgages.
2. **Brokers** can monitor live conversations in a real-time dashboard and take over chats via **Human-in-the-Loop** handoff.
3. **Agencies** get automatically qualified CRM leads, scheduled viewing bookings, and a customizable drop-in website widget.

---

## 📸 Platform Walkthrough & Screenshots

### 1. Platform Super Admin Overview

Global administrative control center displaying live system telemetry, tenant traffic KPIs, active microservices health, and system-wide stats.

<p align="center">
  <img src="https://github.com/user-attachments/assets/08638789-4210-4773-b7cf-f42a10a8c7f9" width="800" alt="Super Admin Overview" />
</p>

---

### 2. Tenants Management & Dual Theme (Dark / Porcelain Light)

Complete agency tenant directory with status toggling, domain whitelisting, and instant key rotation. Built with a full dual-theme system (Luxury Dark `#0B0B0D` & Crisp Porcelain Light `#FFFCF4`).

<p align="center">
  <img src="https://github.com/user-attachments/assets/8b313c95-cb46-4f1a-8b2e-69b4d9ecb92d" width="800" alt="Tenants Management & Dual Theme" />
</p>

---

### 3. One-Click Agency Provisioning & Key Management

Super Admin can instantly onboard new agencies with automated credentials, a secret private API key (`rk_live_...`) for backend integrations, and a public widget key (`wk_live_...`) with strict domain whitelisting.

<p align="center">
  <img src="https://github.com/user-attachments/assets/be2fe89b-db4e-4788-a681-e9dbd60ca02c" width="800" alt="Agency Provisioning Modal" />
</p>

---

### 4. Agency Admin Workspace & Overview

Dedicated agency dashboard featuring high-value KPIs (Today's inquiries, Hot CRM leads, Indexed documents, Grounding rate), quick embed snippet card, and recent hot leads alerts.

<p align="center">
  <img src="https://github.com/user-attachments/assets/2ff45c5d-9e40-4d11-bcaf-43bf91712b3c" width="800" alt="Agency Overview Dashboard" />
</p>

---

### 5. Split 2-Pane Live Conversations & Human Takeover

Interactive 2-pane inbox displaying visitor message transcripts, grounded RAG citations, extracted visitor CRM metadata, and instant human broker takeover action.

<p align="center">
  <img src="https://github.com/user-attachments/assets/fa8c6470-dc9f-4d44-bc90-85653a0a15d2" width="800" alt="Conversations Inbox" />
</p>

---

### 6. Widget Customization & Embed Settings

Interactive 1:1 live preview allowing agencies to customize their widget's accent color, welcome greeting, and quick inquiry prompts, with a ready-to-copy HTML script snippet.

<p align="center">
  <img src="https://github.com/user-attachments/assets/7e4401df-2694-4f61-874c-066a26cb9501" width="800" alt="Widget Customization" />
</p>

---

## Core Features

- **Enterprise Multi-Tenancy**: Complete data isolation across agencies in PostgreSQL and Qdrant Vector DB with cryptographic API/Widget keys.
- **Grounded RAG & Tool Calling**: Answers strictly grounded in uploaded agency documents, with a **LangGraph agent** executing tools for property search, mortgage calculations, and booking viewings.
- **Real-Time Human Handoff (HITL)**: Hybrid Socket.IO & Redis Pub/Sub gateway allowing brokers to take over chats instantly, with auto-return to AI on inactivity.
- **High-Concurrency SSE Streaming**: Token-by-token chat streaming with decoupled database sessions (<5ms checkout) to prevent connection pool exhaustion.
- **Embeddable Web Widget**: Zero-dependency, shadow-DOM isolated TypeScript chat widget ready to embed into any external website with 1 script tag.
- **Dual-Role Management Dashboard**: Luxury dark/light portal built with React 19 and TanStack Router (Super Admin Platform & Agency CRM Workspace).
- **Production Scaling**: Multi-replica FastAPI cluster behind an Nginx load balancer with PgBouncer connection pooling and automated GitHub Actions CI/CD.

## 🛠️ Tech Stack

| Layer                 | Technologies                                                                                             |
| :-------------------- | :------------------------------------------------------------------------------------------------------- |
| **AI & LLM**          | LangGraph, LangChain, Qdrant Vector DB, OpenRouter, Hybrid Search (Dense + Sparse), Grounding Guardrails |
| **Backend API**       | Python (FastAPI), SQLAlchemy 2.0 (Async), Alembic, Pydantic v2, ARQ (Background Workers)                 |
| **Databases & Cache** | PostgreSQL 16, PgBouncer (Transaction Pooling), Redis 7 (Pub/Sub & Rate Limiting)                        |
| **Real-Time**         | Server-Sent Events (SSE), Socket.IO / WebSockets                                                         |
| **Frontend & UI**     | React 19, TypeScript, TanStack Router & Query, Tailwind CSS, Vite, Shadow DOM Widget                     |
| **DevOps & Infra**    | Docker Compose, Nginx, Prometheus, Grafana, GitHub Actions (CI/CD)                                       |

---

## 🏛️ System Architecture

```text
                     ┌──────────────────────────────────────┐
                     │   External Agency Sites & Visitors   │
                     │  (Embeddable Shadow DOM Chat Widget) │
                     └──────────────────┬───────────────────┘
                                        │ HTTPS / SSE / WSS
                                        ▼
                     ┌──────────────────────────────────────┐
                     │          Nginx Reverse Proxy         │
                     └──────────────────┬───────────────────┘
                                        ▼
                     ┌──────────────────────────────────────┐
                     │   FastAPI Cluster (Multi-Replica)    │
                     │  ├── Auth & Tenant Isolation Layer   │
                     │  ├── LangGraph Tool-Calling Agent    │
                     │  └── Real-Time Socket.IO Gateway     │
                     └───────┬──────────────┬──────────────┬┘
                             │              │              │
                             ▼              ▼              ▼
                    ┌────────────────┐ ┌─────────┐ ┌───────────────┐
                    │   PgBouncer    │ │  Redis  │ │ Qdrant Cloud  │
                    │  (Postgres 16) │ │ (Pub/Sub│ │  (Vector DB)  │
                    └────────────────┘ └─────────┘ └───────────────┘
```

---

## 🚀 Quick Start (Local Setup)

### 1. Clone & Configure

```bash
git clone https://github.com/MunawarJamil/realestate_ai.git
cd realestate_ai

cp .env.example .env
```

### 2. Start the Complete Stack with Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### 3. Run the Dashboard Frontend

```bash
cd dashboard
npm install
npm run dev
```

Access the dashboard at [http://localhost:5173](http://localhost:5173).

---

## 🧪 Testing & Code Quality

```bash
# Run backend test suite
uv run pytest

# Type checking & linting
uv run mypy src
uv run ruff check src
```
