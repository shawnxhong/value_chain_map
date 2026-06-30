# Phase 0 — progress log

Plan: `plan/05-phase-0.md`. Goal: prove the spine end-to-end (ingest → parse → extract → verify → graph → click-edge-sees-evidence).

## Task status

| # | Task | Status |
|---|---|---|
| 1 | Scaffold monorepo (backend, frontend, infra, config) | ✅ done |
| 2 | Alembic `0001_init` + Pydantic contracts + write-guard | ✅ done |
| 3 | `llm/` wrapper (Sonnet/Opus, structured output, caching, retry) | ⬜ next |
| 4 | Ingestion (manual upload + EDGAR 10-K) + parse → chunks | ⬜ |
| 5 | Extraction + verification prompts; wire `POST /api/pipeline/run` | ⬜ |
| 6 | Resolution v0 + evidence binding; write `status=candidate` | ⬜ |
| 7 | Minimal review endpoint + audit log | ⬜ |
| 8 | Frontend graph canvas + edge→evidence | ⬜ |
| 9 | Seed 5–10 companies, run pipeline, confirm edges | ⬜ |

---

## Task 1 — Scaffold monorepo ✅

**Date**: 2026-06-30

### What was built

Monorepo skeleton matching `plan/README.md` §Architecture.

- **backend/** — `vcm` Python package (uv project).
  - `pyproject.toml` — core deps (fastapi, uvicorn, pydantic[-settings], sqlalchemy, alembic, psycopg[binary], anthropic, networkx, httpx, pyyaml, python-multipart); `[parse]` extra isolates the heavy Docling/Unstructured stack; `[dev]` = pytest/ruff/mypy. Ruff + mypy + pytest configured here.
  - `vcm/config.py` — `Settings` (pydantic-settings, `VCM_` env prefix) + cached `get_settings()`. Holds DB URL, **model ids** (`extract_model=claude-sonnet-4-6`, `verify_model=claude-opus-4-8`), storage dir, staleness threshold, CORS origins. **Anthropic auth deliberately not here** — the SDK resolves `ANTHROPIC_API_KEY`/`ant` profile at call time (plan/02).
  - `vcm/main.py` — FastAPI app factory; CORS; all routers mounted under `/api`.
  - `vcm/api/health.py` — `GET /api/health` (also the container healthcheck), returns status + version + the two model ids.
  - 14 stub subpackages (`db, models, ingestion, parsing, extraction, verification, resolution, evidence, graph, analytics, review, financials, eval, llm`), each with a one-line responsibility docstring pointing at the relevant plan file.
  - `tests/` — `test_config.py` (defaults + env override), `test_health.py` (TestClient → `/api/health`).
  - `Dockerfile` (python:3.12-slim + uv), `.dockerignore`, `README.md`.
- **frontend/** — Vite 5 + React 18 + TypeScript (pinned to Vite 5 / React 18 for Node 18 host compatibility).
  - `package.json`, `tsconfig.json` (strict, `noUnusedLocals/Parameters`), `vite.config.ts` (dev server on :5173, `/api` proxy → `VITE_API_PROXY` or localhost:8000).
  - `src/main.tsx`, `src/App.tsx` (pings `/api/health` and renders it — proves FE↔BE wiring), `src/api/client.ts` (`apiGet` helper), `src/types/index.ts` (`Health` type), `src/{views,components}/` placeholders.
  - `Dockerfile` (node:20-alpine dev server), `.dockerignore`.
- **infra/** — `docker-compose.yml` (postgres `pgvector/pgvector:pg16` + healthcheck, backend with `/api/health` healthcheck + `depends_on` postgres healthy, frontend), `.env.example`.
- **.gitignore** — extended for Node (`node_modules/`, `frontend/dist/`) and object storage (`/data/`, `backend/data/`).

### Verification (run locally)

| Check | Result |
|---|---|
| `uv venv` + `uv pip install -e ".[dev]"` | ✅ resolved & installed |
| `uv run ruff check .` | ✅ All checks passed |
| `uv run ruff format --check .` | ✅ 22 files already formatted |
| `uv run pytest` | ✅ 3 passed |
| `GET /api/health` via TestClient | ✅ 200 `{status: ok, version: 0.0.0, extract_model: claude-sonnet-4-6, verify_model: claude-opus-4-8}` |
| OpenAPI paths | ✅ `['/api/health']` |
| frontend `npm install` | ✅ (2 advisories — see notes) |
| frontend `npm run typecheck` (`tsc --noEmit`) | ✅ clean |
| frontend `npm run build` (`tsc && vite build`) | ✅ built, 143 kB bundle |
| git ignores `.venv` / `node_modules` / `dist` / `backend/data` | ✅ confirmed |

Lockfiles committed: `backend/uv.lock`, `frontend/package-lock.json`.

### Decisions & deviations

- **`/api` prefix everywhere.** All routers (including health) mount under `/api` so the Vite proxy forwards them unchanged; the backend healthcheck hits `/api/health`. (Plan §04 listed `/api/...` routes; health was unprefixed in the design — moved under `/api` for proxy consistency.)
- **`@types/node` added to the frontend** — `vite.config.ts` reads `process.env.VITE_API_PROXY`, which needs Node types to typecheck. (Caught and fixed during verification.)
- **Alembic deferred to Task 2.** `alembic.ini` + `alembic/` env are part of the migration task, not the scaffold, to keep task boundaries clean. The `db/` package is a stub for now.
- **Vite 5 / React 18, not 6/7** — host Node is 18.19; Vite 6+ wants Node 20+. Containers can use newer Node (frontend Dockerfile uses node:20-alpine), but the pin keeps local `npm run dev` working on the host.

### Environment notes (this machine)

- Python 3.12.3 system; **uv created the venv on CPython 3.13.12** (satisfies `requires-python >=3.12`). Containers pin 3.12-slim.
- **No Docker available locally** — `infra/docker-compose.yml` and both Dockerfiles are written but **not yet validated by an actual `docker compose up`**. Validate on a machine with Docker before relying on the compose path.
- Node v18.19.1 / npm 9.2.0.

### Known low-priority items (not blocking)

- `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2` — surfaced by the installed Starlette; tests still pass. Revisit if/when we pin Starlette.
- `npm audit`: 1 moderate + 1 high (typical vite/esbuild dev-server advisories). Not forcing `audit fix --force` (would break Node 18 compat). Review during a later frontend hardening pass.

### How to run what exists

```bash
# backend
cd backend && uv run uvicorn vcm.main:app --reload   # http://localhost:8000/api/health
cd backend && uv run pytest

# frontend (expects backend on :8000)
cd frontend && npm run dev                            # http://localhost:5173
```

### Next: Task 3 (see bottom)

---

## Task 2 — Alembic `0001_init` + Pydantic contracts + write-guard ✅

**Date**: 2026-06-30

### What was built

Implements `plan/01-data-model.md` for the eight Phase 0 tables.

- **Shared enums** (`vcm/models/enums.py`) — the design's controlled vocabulary as `StrEnum`s (DB + Pydantic share them). 12 DB enums + the analytics/card vocabulary (Pydantic-only until 0002). `CreatedBy.IMPORT = "import"` (keyword-safe member name).
- **Pydantic contracts** (`vcm/models/contracts.py`, re-exported from `vcm/models/__init__.py`):
  - LLM I/O: `CandidateEdge` (+ `CandidateEdgeList`), `EdgeVerdict`, `EconomicDirection` — with the design §9.2 / §7.2 invariants as `model_validator`s.
  - Domain read models (`from_attributes=True`): `Node`, `Company`, `Edge`, `Evidence`.
  - **`StructuralProfileCard`** fully modeled (the Layer-3/4/5 handoff, §5.2) incl. nested `Investability`, `ChainExposure`, `TechMigrationRisk`, `Handoff`, `TierRationale`, `KeyDependencies`. MVP fills required fields; best-effort fields default/optional.
- **SQLAlchemy ORM** (`vcm/db/`):
  - `base.py` — `DeclarativeBase` + constraint **naming convention** (deterministic index/constraint names).
  - `models.py` — 8 tables: `nodes, companies, documents, chunks, evidence, edges, edge_evidence, audit_log`. `_enum()` helper builds Postgres ENUMs whose stored values are the member `.value`. Edge carries the **economic_direction CHECK** and the two **independent ordinal ranks**.
  - `session.py` — **lazy** engine + `sessionmaker`; `get_session()` (FastAPI dep) + `session_scope()` (txn ctx). Lazy so importing never needs a live DB.
  - `repository.py` — `require_evidence_for_fact()` (pure, unit-tested) + `create_edge()` enforcing the **fact-edge-requires-evidence** invariant.
- **Alembic** (`alembic.ini`, `alembic/env.py`, `script.py.mako`, `versions/0001_init.py`):
  - `env.py` reads the DB URL from `vcm.config` (single source of truth) and targets `Base.metadata`; supports offline + online.
  - `0001_init` hand-written: creates the 12 ENUM types once (reused via `create_type=False`), then 8 tables with FKs, indexes, the CHECK, and `server_default`s. Symmetric `downgrade()`.
- **Container migrations**: `docker-entrypoint.sh` runs `alembic upgrade head` then uvicorn; `Dockerfile` now copies `alembic.ini`/`alembic/` and uses the entrypoint.

### Verification (no live DB — used Alembic offline render)

| Check | Result |
|---|---|
| `ruff check .` / `ruff format --check .` | ✅ clean (33 files) |
| `uv run pytest` | ✅ **17 passed** (config, health, contracts, db-metadata, repository) |
| `alembic heads` | ✅ `0001 (head)` |
| `alembic upgrade head --sql` (offline) | ✅ renders: **12 CREATE TYPE**, 8 app tables (+`alembic_version`) |
| CHECK constraint name | ✅ `ck_edges_economic_direction` (after fix — see below) |
| `source_type` enum reuse | ✅ created once, used by `evidence` + `documents` |
| `alembic downgrade 0001:base --sql` | ✅ symmetric: 12 DROP TYPE |
| metadata test | ✅ exactly the 8 expected tables; composite PK on `edge_evidence`; `companies.node_id` PK→FK `nodes` |

### Decisions & fixes

- **Staging/production via `status`** (not separate tables) — as planned (`plan/01` decision). Production = `status='confirmed'`, staging = `'candidate'`.
- **Enums as `StrEnum`** (ruff UP042) — values preserved via explicit assignment; SQLAlchemy `values_callable` stores `.value`.
- **CHECK-constraint name doubling fixed**: Alembic applies the metadata naming convention to op-created constraints, so a pre-prefixed name produced `ck_edges_ck_edges_economic_direction`. Fixed by passing the **bare token** `economic_direction` in the migration (matches the ORM, which relies on the same convention). Re-verified via offline render.
- **`fact`-edge-requires-evidence enforced at the app layer** (`repository.create_edge`) + unit test, per plan wording. A Postgres deferred-constraint trigger is noted as future hardening (needs a live DB to test, so deferred).
- **Deferred to later migrations**: `chunks.embedding` (pgvector) and the `financials` / `profile_cards` tables → Phase 1 migration `0002`.
- `evidence.published_at` / `documents.published_at` made **nullable** (not all sources expose a precise timestamp; the edge `as_of_date` is the load-bearing temporal field).

### Caveats / follow-ups

- **Not yet run against a real Postgres** (no Docker locally). The migration is validated only by offline SQL render. On a Docker host, run `docker compose up` (entrypoint applies `0001`) and ideally `alembic revision --autogenerate` to confirm it diffs to a **no-op** against the ORM models.
- Same Starlette testclient deprecation warning as Task 1 (non-blocking).

---

## Next: Task 3

`llm/` wrapper (`plan/02-pipeline-and-llm.md`): Anthropic client resolving auth from env/`ant` profile; **extraction** via `claude-sonnet-4-6` with structured output (`CandidateEdgeList`); **verification** via `claude-opus-4-8` with adaptive thinking + `effort=high` returning `EdgeVerdict`; prompt caching on the chunk prefix; typed-exception retries; model ids from `config`. Add a smoke test (live, opt-in) asserting both calls return valid structured output and `cache_read_input_tokens > 0` on a shared-prefix second call.
