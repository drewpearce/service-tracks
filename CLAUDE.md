# ServiceTracks — Claude Code Harness

## Product

ServiceTracks syncs Planning Center Online (PCO) worship service plans to streaming playlists (Spotify, YouTube Music). Multi-tenant SaaS — one church per account, one owner per church.

- **Domain**: service-tracks.com
- **Deployed**: Fly.io app `service-tracks` (region: `dfw`)
- **Key terms**: church, plan (a PCO service plan), song mapping (PCO song ↔ streaming track), sync (writing a playlist to a streaming service), streaming connection (OAuth link to Spotify/YouTube Music)

---

## Architecture

Monorepo: `backend/` (FastAPI) + `frontend/` (React SPA). The Dockerfile builds the SPA and serves it as static files from inside the FastAPI process.

### Backend layers (strict top-down — no skipping)

```
routers/  →  services/  →  adapters/
```

- **Routers** handle HTTP, auth dependencies, rate limiting
- **Services** contain business logic, own the transaction (`db.flush()` not `db.commit()`)
- **Adapters** isolate external API calls (PCO, Spotify, YouTube)

### Key backend files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | App factory. **Middleware is LIFO**: Auth registered first (innermost), CSRF last (outermost). |
| `backend/app/config.py` | All env vars via Pydantic `BaseSettings` |
| `backend/app/dependencies.py` | `require_auth` / `require_verified_email` FastAPI deps |
| `backend/app/middleware/auth.py` | Session cookie → `request.state.current_user` + `church_id` |
| `backend/app/adapters/streaming.py` | Factory: `get_streaming_adapter(platform)` → Spotify or YouTube adapter |
| `backend/app/services/sync_service.py` | Core sync engine. Uses `db.flush()`; caller commits. |
| `backend/app/scheduler.py` | APScheduler, 10-concurrent-sync semaphore, 60s timeout, per-church jitter |
| `backend/app/utils/encryption.py` | Fernet encrypt/decrypt for stored OAuth tokens |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/App.tsx` | React Router v6 routes (public + `ProtectedRoute`-wrapped) |
| `frontend/src/api/client.ts` | Fetch wrapper. Adds `X-CSRF-Token` from `csrf_token` cookie. Redirects to `/login` on 401. |
| `frontend/src/types/api.ts` | TypeScript interfaces mirroring Pydantic schemas — keep in sync manually |
| `frontend/src/hooks/useAuth.tsx` | Auth context + `useAuth()` hook |

### Database / auth / security

- PostgreSQL, async SQLAlchemy 2.0. Alembic migrations in `backend/alembic/versions/`.
- Tests use per-test transaction rollback (see `backend/tests/conftest.py`).
- **Auth**: `session` cookie (JWT) → DB lookup → `request.state.current_user` / `church_id`
- **CSRF**: `csrf_token` cookie + `X-CSRF-Token` header (starlette-csrf, exempt: `/health`, auth, webhooks, OAuth callbacks)
- **OAuth tokens**: encrypted at rest with Fernet (`utils/encryption.py`)
- **Logging**: structlog with keyword args (`logger.info("event", key=val)`). Never f-strings in log calls.
- **Errors**: Sentry for uncaught exceptions. `fly logs` for structured logs in prod.

---

## Dev Commands

Prerequisites: Docker (for Postgres), uv, Node 20+

```bash
make dev-db        # start Postgres in Docker
make migrate       # alembic upgrade head
make backend       # FastAPI with hot reload → localhost:8000
make frontend      # Vite dev server → localhost:5173
make test          # pytest
make test-cov      # pytest with coverage report
make lint          # ruff check
make format        # ruff format
make install       # uv sync + npm install
```

New migration:
```bash
cd backend && uv run alembic revision --autogenerate -m "description"
```

Production:
```bash
fly logs               # structured log tail
fly ssh console        # SSH into running instance
flyctl deploy --remote-only  # manual deploy (CI does this on main push)
```

---

## Code Conventions

### Backend

- **Router pattern**: `router = APIRouter(prefix="/api/<resource>", tags=["<resource>"])`. Protected routes use `Depends(require_verified_email)`. Access church from `request.state.church_id`.
- **Service pattern**: async functions, `db: AsyncSession` as first arg. Call `db.flush()` (not `db.commit()`) — routers own commit.
- **Model pattern**: SQLAlchemy 2.0 `Mapped`/`mapped_column`, `Uuid` PKs (`default=uuid.uuid4`), `DateTime(timezone=True)`.
- **Schema pattern**: Pydantic v2 in `schemas/`. Separate request/response schemas. Never use ORM models directly in responses.
- **Error handling**: Raise `HTTPException` in routers. Raise typed custom exceptions in adapters (e.g., `PcoApiError`, `YouTubeAuthError`). Services catch and convert as needed.
- **Python deps**: Always `uv` — never `pip`. `uv add <pkg>` to add, `uv sync` to install from lock.
- Type annotations required on all function signatures.

### Frontend

- All API calls go through `apiClient()` in `api/client.ts`. Never use raw `fetch` directly.
- `types/api.ts` must mirror backend Pydantic schemas. Update both together.
- `useAuth()` for current user/church state.

### Testing

- All backend tests are async (`asyncio_mode = "auto"` in `pyproject.toml`).
- External HTTP mocked with `respx`. No real network calls in tests.
- Per-test DB isolation via transaction rollback — see `conftest.py`.
- Test DB: `TEST_DATABASE_URL` env var (CI uses SQLite in-memory, local uses Postgres).
- No frontend tests currently.

---

## Workflow

- Always work on a branch named `<issue-number>-<short-slug>` (e.g., `7-pco-oauth`). Merge to `main` via PR. Never commit directly to `main`.
- PRs reference their issue: `Closes #7`
- Run pre-commit hooks before pushing: `pre-commit run --all-files` (ruff lint+format, tsc, eslint)
- Use `uv` for all Python operations — never `pip`
- The product is **ServiceTracks** (not "WorshipFlow")

---

## Issue Tracking

Tasks are tracked in GitHub Issues.

```bash
gh issue list                          # see open issues
gh issue list --label "ready"          # see issues ready to pick up
gh issue view 7                        # read full issue context
```

**Labels:**

| Label | Meaning |
|-------|---------|
| `type: feature` | New user-facing capability |
| `type: bug` | Something broken |
| `type: chore` | Refactor, tooling, cleanup |
| `type: infra` | Hosting, CI, deployment |
| `area: backend` | Python/FastAPI/database |
| `area: frontend` | React/TypeScript |
| `area: sync` | PCO/streaming integration and sync logic |
| `priority: high` | Blocking or critical path |
| `ready` | Fully scoped, can be picked up immediately |
| `needs-design` | Requires exploration or decision first |

---

## Key Context by Area

| Working on... | Read these files first |
|---------------|----------------------|
| New API endpoint | `routers/plans.py`, `services/sync_service.py` |
| New streaming platform | `adapters/streaming.py`, `adapters/spotify_adapter.py` |
| Auth / session logic | `middleware/auth.py`, `dependencies.py` |
| New DB model + migration | `models/church_user.py`, `alembic/versions/001_initial_schema.py` |
| Frontend API integration | `api/client.ts`, `types/api.ts` |
| Scheduler / background jobs | `scheduler.py` — note `db.flush()` vs `db.commit()` contract in sync_service |
| OAuth flow | `routers/streaming.py`, `middleware/auth.py` (exempt patterns) |
