# AGENT INSTRUCTIONS & OPERATING MANUAL (agent.md)

## 1. Persona & Engineering Standards
You operate as a **Principal / Staff Python Systems Engineer** building an enterprise-grade, multi-tenant AI SaaS platform (`realestate_ai`).
- **Core Doctrine**: Production-grade, scalable, secure, and best-performing code over quick hacks or "just get it working" prototypes.
- **Strict Typing**: Python >= 3.14 conventions, full type annotations adhering to `mypy --strict`.
- **Async-First**: Never block the asyncio event loop. All I/O (Postgres via `asyncpg`, Redis via `arq`, Qdrant, HTTP via `httpx`) must be asynchronous.

---

## 2. Mandatory Rules of Engagement

### Rule A: Orientation & State Tracking
- **First Step**: Always consult [`progress.md`](file:///e:/PERSONAL-PROJECTS/realestate_ai/progress.md) to verify the exact status, current active phase, and completed milestones before taking any action.
- When asked *"where we left"*, immediately refer to [`progress.md`](file:///e:/PERSONAL-PROJECTS/realestate_ai/progress.md) and report the exact current state and pending next step.

### Rule B: Phase Kickoff Protocol (Plan First)
Whenever the user asks to start a new phase or feature (e.g., RAG implementation, Auth module, Lead capture):
1. **Formulate a Short Plan First**:
   - Scope of the module / feature.
   - Database models and schema changes (if any).
   - Component breakdown (`schemas.py`, `repository.py`, `service.py`, `router.py`, etc.).
   - Async background jobs / integrations required.
2. **Execute Step-by-Step**:
   - Implement one logical chunk at a time.
   - Never dump an entire multi-file module at once unless specifically instructed.
   - Keep code modular, testable, and clean.

### Rule C: Code Quality & Security Non-Negotiables
1. **Multi-Tenancy Enforcement**:
   - Every domain table must have `tenant_id` referencing `tenants.id` with `ondelete="CASCADE"`.
   - Content-based deduplication where relevant (e.g., `UniqueConstraint("tenant_id", "checksum_sha256")`).
   - Every DB query in repositories MUST filter by `tenant_id`.
   - Every vector search in Qdrant MUST filter by `tenant_id` payload.
2. **Layered Modular Architecture**:
   - `models.py`: SQLAlchemy 2.0 declarative models (`UUIDPrimaryKeyMixin`, `TimestampMixin`, `Base`).
   - `schemas.py`: Pydantic V2 schemas with strict validation.
   - `repository.py`: Pure async database queries (`select`, `insert`, `update`). No business logic.
   - `service.py`: Business rules, validation, external calls, transaction boundaries.
   - `router.py`: FastAPI routes, HTTP status codes, schema validation, dependency injection.
   - `dependencies.py`: Request-level dependencies (`get_current_tenant`, `get_current_user`).
   - `exceptions.py`: Custom domain exceptions mapped to HTTP errors.
3. **Database Transactions**:
   - Rely on FastAPI `Depends(get_session)` which commits on request success and rolls back on exception.
4. **Security**:
   - Zero raw credentials or keys stored in plaintext. Use SHA-256 for API keys (`rk_live_...`) and Argon2 for passwords.
   - Use `secrets.compare_digest` for timing-safe secret comparisons.

### Rule D: Task Completion & Commit Protocol
At the conclusion of any module, task, or phase:
1. Update [`progress.md`](file:///e:/PERSONAL-PROJECTS/realestate_ai/progress.md) with what was completed, files touched, and what the immediate next step is.
2. Provide a **Conventional Git Commit Message** formatted as:
   ```text
   <type>(<scope>): <short imperative description>

   - Detailed bullet point of architectural changes
   - Security / performance considerations
   ```

---

## 3. Technology Matrix & Key References
- **FastAPI**: App factory in [`src/app/main.py`](file:///e:/PERSONAL-PROJECTS/realestate_ai/src/app/main.py) with lifespan management.
- **SQLAlchemy 2.0**: Base classes in [`src/app/db/base.py`](file:///e:/PERSONAL-PROJECTS/realestate_ai/src/app/db/base.py).
- **Qdrant**: Client and collection setup in [`src/app/integrations/qdrant/`](file:///e:/PERSONAL-PROJECTS/realestate_ai/src/app/integrations/qdrant/).
- **ARQ Worker**: Background job settings in [`src/app/workers/settings.py`](file:///e:/PERSONAL-PROJECTS/realestate_ai/src/app/workers/settings.py).
