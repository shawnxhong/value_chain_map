# Phase 0 — progress log

Plan: `plan/05-phase-0.md`. Goal: prove the spine end-to-end (ingest → parse → extract → verify → graph → click-edge-sees-evidence).

## Task status

| # | Task | Status |
|---|---|---|
| 1 | Scaffold monorepo (backend, frontend, infra, config) | ✅ done |
| 2 | Alembic `0001_init` + Pydantic contracts + write-guard | ✅ done |
| 3 | `llm/` wrapper (Sonnet/Opus, structured output, caching, retry) | ✅ done |
| 4 | Ingestion (manual upload + EDGAR 10-K) + parse → chunks | ✅ done |
| 5 | Extraction + verification prompts; wire `POST /api/pipeline/run` | ✅ done |
| 6 | Resolution v0 + evidence binding; write `status=candidate` | ⬜ next |
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

## Task 3 — `llm/` wrapper ✅

**Date**: 2026-06-30

Implements `plan/02-pipeline-and-llm.md` §LLM layer. Verified the SDK surface against the
`claude-api` skill before writing (anthropic **0.113.0** installed): `messages.parse` is the
structured-output entry point and accepts `output_format` (Pydantic model), `output_config`,
and `thinking` together — internally it does `{**output_config, "format": ...}`, so `effort`
and the schema coexist.

### What was built

- **`vcm/llm/client.py`** — `get_client()`: cached zero-arg `anthropic.Anthropic(max_retries=…)`.
  Auth resolves at call time from `ANTHROPIC_API_KEY` or an `ant` profile (never in `config`);
  `max_retries` from the new `Settings.llm_max_retries` (default 2). Lazy — never called at
  import, only inside a request, so the default test run needs no credentials/network.
- **`vcm/llm/errors.py`** — `LLMError` base + `LLMConnectionError` / `LLMRateLimitError` /
  `LLMAuthError` / `LLMBadRequestError` / `LLMServiceError` / `LLMRefusalError`. Each carries
  `model` + `request_id`. This is the typed surface callers branch on (retryable vs terminal)
  instead of string-matching SDK errors.
- **`vcm/llm/calls.py`** — the mechanism layer:
  - `build_parse_kwargs(...)` — **pure** request assembler (unit-tested offline). Puts
    instructions+chunk in the first content block with a `cache_control` breakpoint and the
    per-call **question after it, uncached** → re-reading the same chunk hits the cache
    (plan/02 "cache the chunk prefix; vary the per-edge question").
  - `LLMResult[T]` — frozen dataclass: `parsed`, `usage` (carries `cache_read_input_tokens`),
    `model`, `request_id`, `stop_reason`. PEP-695 generics to satisfy ruff UP046/UP047.
  - `_run_parse(...)` — calls `messages.parse`, maps SDK exceptions **most-specific-first**
    (`APIConnectionError` → `RateLimitError` → auth → bad-request/not-found → `APIStatusError`),
    and raises `LLMRefusalError` on `stop_reason=='refusal'` or `parsed_output is None`.
  - `extract_edges(chunk, …)` → `CandidateEdgeList` on `config.extract_model` (Sonnet), no thinking.
  - `verify_edge(chunk, claim, …)` → `EdgeVerdict` on `config.verify_model` (Opus), **adaptive
    thinking + `effort=high`** (the correctness gate).
- **`vcm/llm/__init__.py`** — re-exports the public surface (14 names).
- **`vcm/config.py`** — added `llm_max_retries: int = 2`.

### Verification

| Check | Result |
|---|---|
| `ruff check .` / `ruff format --check .` | ✅ clean (38 files) |
| `mypy vcm` | ✅ no issues (28 source files) |
| `pytest` | ✅ **32 passed, 2 skipped** (smoke tests skip without opt-in) |
| offline `tests/test_llm.py` | ✅ 15 tests: cache-prefix placement, model/thinking/effort wiring, result wrapping, refusal path, full exception-mapping matrix (built real `anthropic` errors from a fabricated `httpx.Response`) |
| **live** `tests/test_llm_smoke.py` (`VCM_LLM_SMOKE=1`) | ✅ **2 passed (59s)** against the real API — Sonnet extract → valid `CandidateEdgeList`, Opus verify (adaptive thinking + `effort=high`) → valid `EdgeVerdict`, and `cache_read_input_tokens > 0` on the shared-prefix second call for **both** models |
| import surface | ✅ `vcm.llm.__all__` resolves |

### Decisions & deviations

- **Prompts are Phase-0 placeholders.** `calls.py` ships terse but correct extract/verify
  instructions (incl. §9.2 prohibitions: excerpt-required-for-fact, don't-rewrite-hedged,
  SUPPLIES_TO needs `economic_direction`) so the smoke test produces valid output. The **full**
  prompts + anonymous-customer handling are Task 5 (`extraction/`, `verification/`), which call
  `extract_edges`/`verify_edge`/`build_parse_kwargs` from here. Kept task boundaries clean.
- **`messages.parse`, not `messages.create` + manual JSON.** Validates against the Pydantic
  contract automatically (incl. the cross-field `model_validator`s) — the design's quality gate.
- **Caches are model-scoped**, so extraction (Sonnet) and verification (Opus) do **not** share a
  cache prefix; the win is repeated calls on the *same* model (e.g. verifying many edges from one
  chunk). The smoke test asserts caching with two same-model, same-prefix calls.
- **`max_tokens=16000` non-streaming** for both — above EdgeVerdict / a chunk's edge list and
  under the SDK's ~10-min non-streaming timeout guard. Stream + raise only if a chunk ever needs a
  very long edge list (deferred).
- **Typed-exception *handling*, SDK does the *backoff*.** The SDK auto-retries 429/5xx/connection
  with exponential backoff (`max_retries`); our chain classifies what survives into `LLMError`s.

### Caveats / follow-ups

- **Live smoke test now run and passing** (2026-06-30, key from `infra/.env`): `VCM_LLM_SMOKE=1
  uv run pytest tests/test_llm_smoke.py` → 2 passed. Confirms valid structured output from both
  models and real prompt-cache reads on the shared-prefix second call (chunk sized > 4096 tokens,
  the Opus 4.8 minimum cacheable prefix). Default `pytest` still skips these (opt-in, billed).
- **Proxy gotcha on this machine**: the env sets both `https_proxy` (http) and `ALL_PROXY=socks5://…`;
  httpx prefers the SOCKS one and `socksio` isn't installed, so the live run needs
  `env -u ALL_PROXY -u all_proxy` (falls back to the HTTP proxy) — or `uv pip install "httpx[socks]"`.
  Offline tests are unaffected.
- Same Starlette testclient deprecation warning as Tasks 1–2 (non-blocking).

---

## Task 3b — multi-provider (OpenAI + DeepSeek) ✅

**Date**: 2026-06-30

Implements the `plan/` multi-provider design (plan/02 §LLM layer). The Anthropic-only wrapper
was refactored into a provider-pluggable seam behind the **unchanged public API**
(`extract_edges` / `verify_edge` / `LLMResult` / `LLMError`). Anthropic stays the default;
OpenAI and DeepSeek are selectable per role via config. Verified the OpenAI SDK surface first
(openai **2.44.0**): `chat.completions.parse(response_format=…)` → `message.parsed`, usage
`prompt_tokens_details.cached_tokens`, `CompletionUsage` is `extra="allow"` (so DeepSeek's
`prompt_cache_hit_tokens` is reachable), and the exception hierarchy mirrors `anthropic.*`.

### What changed

- **`vcm/llm/base.py`** (new) — provider-neutral types: `StructuredLLM` protocol,
  `ParseRequest[T]`, `LLMResult[T]` (gained `provider`; `usage` is now neutral `LLMUsage`
  = `input_tokens` / `output_tokens` / `cached_input_tokens`; `stop_reason` → `finish_reason`).
- **`vcm/llm/providers/anthropic.py`** — `AnthropicProvider` (the old `calls.py` logic:
  `cache_control` + adaptive `thinking` + `output_config.effort`).
- **`vcm/llm/providers/openai_compat.py`** — `OpenAICompatibleProvider`, one class for **both**
  OpenAI and DeepSeek. `json_schema` mode (OpenAI) uses `chat.completions.parse`; `json_object`
  mode (DeepSeek) runs JSON mode + injects the schema into the system prompt + validates with
  `model_validate_json` (DeepSeek has no strict json_schema). `reasoning_effort` is sent only for
  reasoning models (`o*`/`gpt-5*`) when reasoning is requested; usage normalized across both.
- **`vcm/llm/registry.py`** (new) — `get_provider(LLMProvider)` cached factory.
- **`vcm/llm/calls.py`** — now provider-neutral; selects the provider from config (or an injected
  impl for tests) and builds a `ParseRequest`. Prompts moved to **`vcm/llm/prompts.py`**.
- **`vcm/config.py`** — `extract_provider` / `verify_provider: LLMProvider = anthropic`,
  `deepseek_base_url`. **`vcm/models/enums.py`** — `LLMProvider` enum. **`pyproject.toml`** — added
  `openai>=1.40` (installed 2.44.0; DeepSeek reuses it via `base_url`).
- Auth resolves per provider from env at call time (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` /
  `DEEPSEEK_API_KEY`); a missing key → `LLMAuthError`.

### Verification

| Check | Result |
|---|---|
| `ruff` / `ruff format` / `mypy vcm` | ✅ clean (34 source files) |
| `pytest` (offline) | ✅ **41 passed, 6 skipped** — rewrote `test_llm.py`: call wiring, all three providers' request assembly + usage normalization + refusal + exception mapping (real `anthropic.*` **and** `openai.*` errors), registry |
| **live** `tests/test_llm_smoke.py` (`VCM_LLM_SMOKE=1`) | ✅ **6 passed (≈83s)** — parametrized over all three providers; each returns a valid `CandidateEdgeList` (extract) + `EdgeVerdict` (verify), and `cached_input_tokens > 0` on the shared-prefix second call (strict for Anthropic, best-effort for OpenAI/DeepSeek — both registered, no skips) |

Smoke models: Anthropic `claude-sonnet-4-6`/`claude-opus-4-8`; OpenAI `gpt-4o-mini`/`o4-mini`;
DeepSeek `deepseek-chat`/`deepseek-chat`.

### Decisions & caveats

- **`gpt-5*` needs org verification on this account** (404 `model_not_found`) — surfaced correctly
  as `LLMBadRequestError`. Switched OpenAI verify to **`o4-mini`** (a reasoning model, so it
  exercises the `reasoning_effort` path) after probing which models the account can call.
- **DeepSeek = OpenAI SDK + `base_url`**, `json_object` mode, `max_tokens` (not
  `max_completion_tokens`), no `reasoning_effort`. JSON-validate failure → `LLMRefusalError`.
- **Effort mapping**: neutral `low/medium/high/xhigh/max` → OpenAI `reasoning_effort` clamps to
  `low/medium/high`; Anthropic passes through.
- **Public API unchanged** — only the (white-box) internals moved, so `test_llm.py` was rewritten
  but `extract_edges`/`verify_edge`/`LLMResult`/errors keep their shape. `build_parse_kwargs` is now
  a private `AnthropicProvider` method.
- Live run uses the same `env -u ALL_PROXY -u all_proxy` proxy workaround as Task 3.

---

## Task 4 — Ingestion + parsing ✅

**Date**: 2026-06-30

Implements `plan/02` §Ingestion/§Parsing + `plan/05` Task 4: raw source → object store +
`documents`, parse → chunks → `chunks`. Manual upload **and** SEC EDGAR 10-K fetch.

### What was built

- **`vcm/ingestion/store.py`** — `ObjectStore`: content-addressed local FS store under
  `config.storage_dir`, keyed by SHA-256 and sharded by the first 2 hex chars. Idempotent
  (re-ingesting identical bytes is a no-op); the key is `documents.storage_path`.
- **`vcm/ingestion/edgar.py`** — SEC EDGAR fetch. Pure, unit-tested helpers (`normalize_cik`,
  `resolve_cik` via `company_tickers.json`, `pick_latest_filing` over `filings.recent`
  newest-first arrays, `archive_url`); `fetch_latest_10k` does the live HTTP with the required
  `User-Agent` (`config.edgar_user_agent`). `IngestionError` for unknown ticker / missing form.
- **`vcm/parsing/parse.py`** — `parse_document(raw, content_type, filename)` dispatch:
  text/markdown decode through; **HTML flattened with a stdlib `HTMLParser`** (drops
  script/style, block tags → newlines) — zero heavy deps, so the 10-K (HTML) path works
  out of the box. PDF is routed to **Docling (the `[parse]` extra), lazy-imported**; without it,
  a clear `ParsingError` with install guidance (PDF not needed for the Phase-0 DoD).
- **`vcm/parsing/chunk.py`** — `chunk_text`: greedy paragraph packing to `config.chunk_target_chars`
  (~1.5k tokens), byte-accurate `char_start/char_end` (an excerpt can later be located in its
  chunk), oversized paragraphs hard-split, ~4-chars/token `token_count` estimate.
- **`vcm/ingestion/service.py`** — orchestration: `ingest_document` (store → parse → chunk →
  persist `documents` + `chunks`, flush-not-commit so the caller owns the txn) + pure ORM-row
  builders; `ingest_upload` and `ingest_edgar_10k` wrappers.
- **`vcm/api/pipeline.py`** — `POST /api/pipeline/ingest` (multipart upload) and
  `POST /api/pipeline/ingest/edgar` (JSON `{ticker_or_cik, form}`), mounted under `/api`.
  Both commit via `session_scope`. (`POST /api/pipeline/run` = Task 5.)
- **`vcm/config.py`** — `edgar_user_agent`, `chunk_target_chars`. **`pyproject.toml`** — ruff
  `flake8-bugbear.extend-immutable-calls` whitelist for FastAPI `File`/`Form`/`Depends`/`Query`.
  No new core deps (httpx + python-multipart already present).

### Verification

| Check | Result |
|---|---|
| `ruff` / `ruff format` / `mypy vcm` | ✅ clean (40 source files) |
| `pytest` (offline) | ✅ **64 passed, 7 skipped** — `test_parsing.py` (HTML flatten, chunk offsets/packing/hard-split, dispatch incl. PDF-without-extra raises), `test_ingestion.py` (object store, EDGAR pure helpers, **SQLite persistence** of `documents`+`chunks` incl. HTML-parsed path), `test_pipeline_api.py` (routes registered, 422 validation paths without a DB) |
| **live** `tests/test_ingestion_live.py` (`VCM_EDGAR_LIVE=1`) | ✅ **1 passed (~10s)** — fetched Microsoft's real 10-K (CIK 0000789019), flattened HTML (>5k chars, no tags), chunked |
| **live end-to-end** (manual) | ✅ `ingest_edgar_10k("NVDA")` → SQLite: NVIDIA 10-K (acc `0001045810-26-000021`, filed 2026-02-25) stored + **65 chunks** persisted (1 `documents` + 65 `chunks`) |

### Decisions & caveats

- **Persistence tested on in-memory SQLite** (just `documents`+`chunks`, which use no PG-only
  types) — real coverage of the write path without Docker/Postgres. The full stack is for the
  docker-compose DoD.
- **HTML via stdlib, not Unstructured.** The plan named Docling+Unstructured; for Phase 0 the
  stdlib `HTMLParser` flattens 10-K HTML well enough to prove the spine with zero heavy deps.
  Docling is wired (lazy) for PDF and **untested locally** (not installed) — verify its API when
  `[parse]` is first installed. Unstructured/Docling for richer HTML/deck parsing is a follow-up.
- **Chunk hashing not persisted**: the `chunks` table (migration 0001) has no hash column; the
  design's hashing is `evidence.excerpt_hash` (Task 6). `token_count` is a documented estimate.
- **EDGAR is manual/on-demand** (design §11 P0): no crawling; SEC `User-Agent` required; live runs
  use the `env -u ALL_PROXY -u all_proxy` proxy workaround (Tasks 3/3b).
- Chunks are the input to Task 5's `extract_edges` (Task 3) → `POST /api/pipeline/run`.

---

## Task 5 — Extraction + verification pipeline ✅

**Date**: 2026-06-30

Implements `plan/05` Task 5 + `plan/02` §9.1: the deterministic two-stage pipeline over a
document's chunks — extract candidate edges, then verify each against its own chunk — wired to
`POST /api/pipeline/run`. Writing edges (resolution + evidence binding) is **Task 6**; this task
returns the verified candidates.

### What was built

- **`vcm/llm/prompts.py`** — replaced the Phase-0 placeholders with the **full** extraction /
  verification prompts: relationship-type + layer definitions, the §9.2 prohibitions
  (excerpt-required-for-fact, no hedged→certain, no invented counterparties), explicit
  `economic_direction` rules, **anonymous-major-customer (ASC 280)** handling, and the verifier's
  downgrade/reject rubric. Provider-neutral (drives Anthropic/OpenAI/DeepSeek).
- **`vcm/extraction/__init__.py`** — `extract_candidates(chunk) -> ExtractionResult`: thin wrapper
  over `llm.extract_edges`, returns the candidate list + normalized usage.
- **`vcm/verification/__init__.py`** — `format_claim(candidate)` (renders an edge into the per-edge
  claim that rides the cached chunk prefix) + `verify_candidate(chunk, candidate) -> VerificationResult`.
- **`vcm/pipeline.py`** — the orchestrator: `run_chunks(chunks, …)` (extract → per-edge verify;
  supported edges kept with the verifier's **corrected layer/confidence** via `model_copy`;
  refusals skip the chunk/edge and are counted, not fatal; usage aggregated) and
  `run_document(session, document_id, max_chunks=…)` (loads ordered `chunks`, 404s on unknown doc /
  no chunks). `PipelineError`, `VerifiedEdge`, `PipelineResult`.
- **`vcm/api/pipeline.py`** — `POST /api/pipeline/run` (`{document_id, max_chunks?}`) →
  `PipelineRunResponse` (counts + verified edges with their verdict reason). Read-only in Task 5.

### Verification

| Check | Result |
|---|---|
| `ruff` / `ruff format` / `mypy vcm` | ✅ clean (41 source files) |
| `pytest` (offline) | ✅ **70 passed, 8 skipped** — `test_pipeline.py` (run_chunks with injected fake providers: supported/unsupported split, verdict-correction application, extract/verify refusal handling, ordinal tracking, usage aggregation, `format_claim`); `test_pipeline_api.py` (run route registered, 422) |
| **live** `tests/test_pipeline_live.py` (`VCM_LLM_SMOKE=1`) | ✅ **1 passed (~76s)** — extract (Sonnet) + verify (Opus) on a real chunk |
| **live end-to-end** (Task 4 + 5, manual) | ✅ upload transcript → 1 chunk (SQLite) → `run_document`: **13 extracted, 11 verified, 2 rejected** by the gate; verifier downgraded weak edges (Micron→NVIDIA to inference/low); prompt cache reused 12,756 input tokens across the 13 verify calls. Verified edges are the HBM→packaging→GPU structure (SK Hynix/TSMC SUPPLIES_TO NVIDIA, NVIDIA PRODUCES H100/H200, …) |

### Decisions & caveats

- **Task boundary**: `/run` returns verified candidates; it does **not** write nodes/edges/evidence
  (Task 6: resolution v0 + evidence binding + `status=candidate`, with the fact-needs-evidence guard).
  `session_scope` is read-only here.
- **Verifier corrections** applied via `model_copy(update=…)` (no re-validation), so a rare
  fact-upgrade-without-excerpt is left for Task 6's write-time guard to reject.
- **Prompts live in `vcm/llm/prompts.py`** (the mechanism layer's defaults) rather than duplicated in
  `extraction/`/`verification/` — those packages own orchestration and import the llm functions
  (clean layering: pipeline → extraction/verification → llm).
- **Cost**: `max_chunks` bounds a run; refusals are tolerated per chunk/edge. A full 10-K (65 chunks)
  run is left to the docker-compose DoD.

---

## Next: Task 6

Resolution v0 + evidence binding (`plan/05` Task 6): exact ticker/alias → `nodes` resolution
(incl. anonymous-customer nodes), bind each verified candidate's `excerpt` as an `evidence` row, and
write `edges` with `status=candidate` — enforcing the fact-edge-requires-evidence invariant
(`repository.create_edge`, already built in Task 2) at write time. Extends `POST /api/pipeline/run`
to persist the `VerifiedEdge`s the pipeline now returns.
