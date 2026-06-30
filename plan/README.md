# Value Chain Map (VCM) — Development Plan

> **Baseline design**: `docs/value_chain_map_design.md` (v0.3) is the source of truth. This `plan/` directory turns that design into an executable engineering plan. Where this plan and the design disagree, the design wins unless this plan explicitly records a decision overriding it.

## Plan index

| File | Covers |
|---|---|
| `README.md` (this) | Context, architecture & repo layout, phase map, cross-cutting concerns |
| `01-data-model.md` | PostgreSQL schema (DDL sketches) + Pydantic contracts |
| `02-pipeline-and-llm.md` | LLM split (Sonnet extract / Opus verify), prompts, deterministic pipeline, anonymous customers |
| `03-analytics-and-cards.md` | Profit pool / bottleneck / weak-link checklists + Structural Profile Card contract |
| `04-api-and-frontend.md` | FastAPI surface + React/Cytoscape UI |
| `05-phase-0.md` | Phase 0 technical-validation spike (deep: tasks + DoD) |
| `06-phase-1.md` | Phase 1 HBM→packaging→GPU MVP (deep: tasks + DoD) |
| `07-phases-2-3-outline.md` | Phase 2–3 roadmap (outline) |
| `08-evaluation-and-verification.md` | Gold-set eval, testing strategy, end-to-end verification |

---

## Context

The repo currently holds only design docs (`docs/`, `history/`). There is **no code yet** — this is a greenfield build.

VCM is the **Layer-2 (industry structure & value chain) map engine** of a five-layer tech-stock research toolset. It ingests evidence (transcripts, decks, 10-K/XBRL), uses an LLM pipeline to extract **evidence-bound** candidate relationships, gates them through verification + human review into a property graph, and produces two outputs: an **interactive value-chain map** and a per-company **Structural Profile Card** (`consider / watch / structurally_excluded`) that hands off to Layers 3–5. It does **not** make buy/sell calls.

**Build success (design §4.3)**: after loading one sub-chain, a user can state who is strong/weak, where profit pools, where profit is migrating, and which companies to exclude — every claim traceable to an excerpt.

---

## Decisions taken for this plan

| Decision | Choice | Rationale / source |
|---|---|---|
| LLM split | extraction = `claude-sonnet-4-6`; verification = `claude-opus-4-8` | Cost on the high-volume pass, quality on the correctness gate |
| LLM provider | pluggable — Anthropic (default), OpenAI, DeepSeek; selectable per role | Multi-provider behind one interface (`02-pipeline-and-llm.md` §LLM layer); Anthropic default preserves current behavior |
| UI | interactive React + Cytoscape from Phase 0 | Design §15; the map is a core deliverable |
| Plan depth | Phase 0 & 1 fully specified; Phase 2–3 outlined | MVP is where execution detail matters |
| Storage | relational-first: PostgreSQL (edges as rows) + NetworkX (in-memory) | Design §12; 50–500 edges don't need a graph DB |
| Pipeline | deterministic two-prompt (extract → verify) + human review | Design §9.1; no multi-agent orchestration in MVP |
| Staging vs production | one `edges` table, `status` field discriminates | Relational-first simplification of design §5.3 (see `01-data-model.md`) |

---

## Architecture & repo layout

Monorepo, local-first, Docker Compose.

```
value_chain_map/
  docs/            # existing — design baseline + changelog (source of truth)
  history/         # existing — archived design evolution
  plan/            # this plan
  backend/
    vcm/
      config.py            # pydantic-settings: DB URL, provider + model ids, thresholds (provider auth via env)
      db/                  # SQLAlchemy models, Alembic migrations, session factory
      models/              # Pydantic domain models + LLM I/O schemas (the contracts)
      ingestion/           # source manager: manual upload + SEC EDGAR (10-K/XBRL) fetch
      parsing/             # Docling/Unstructured -> markdown/chunks; chunk hashing
      extraction/          # extract prompt (Sonnet) -> candidate edges
      verification/        # verify prompt (Opus) -> support verdict per edge
      resolution/          # entity resolver (ticker/CIK/alias -> node), incl. anonymous-customer nodes
      evidence/            # evidence store: excerpt + hash + provenance
      graph/               # Postgres edge store + NetworkX builder + graph queries
      analytics/           # profit pool, bottleneck/weak-link checklists, profile-card generator
      review/              # status transitions + audit log (staging->production)
      financials/          # XBRL company-facts ingest + cross-stage metric comparison
      eval/                # gold-set harness: precision/recall/faithfulness/layer-correctness
      api/                 # FastAPI routers (graph, evidence, review, pipeline, cards)
      llm/                 # Anthropic client wrapper: structured output, caching, retries, batches
    tests/
    pyproject.toml
    alembic.ini
  frontend/                # React + Vite + TypeScript + Cytoscape.js
    src/{views,components,api,types}/
  infra/
    docker-compose.yml     # postgres(+pgvector), backend, frontend
    .env.example
  seeds/
    hbm_subchain.yaml      # Phase 1 seed: nodes + stages for HBM->packaging->GPU->server->hyperscaler
    gold_edges.yaml        # 20-30 hand-labeled relationships for eval
```

**Why this shape**: the design's modules (§8.2) map 1:1 to `backend/vcm/*` packages; `models/` holds the Pydantic contracts that drive structured extraction (§12) and the profile-card interface (§5.2); `graph/` isolates the "Postgres rows + NetworkX" decision (§12) so a later swap to Kuzu/Neo4j touches only that package.

---

## Phase map

| Phase | Goal | Detail |
|---|---|---|
| **0** (1–2 wk) | Prove the spine end-to-end: ingest → parse → extract → verify → graph → click-edge-sees-evidence | `05-phase-0.md` |
| **1** (3–6 wk) | Usable single sub-chain (HBM→packaging→GPU→server→hyperscaler) with analytics + profile cards | `06-phase-1.md` |
| **2** (6–10 wk) | Incremental updates, graph diff, layer interfaces | `07-phases-2-3-outline.md` |
| **3** (10 wk+) | Multi sub-chain breadth, link prediction, graph-DB migration if needed | `07-phases-2-3-outline.md` |

---

## Cross-cutting concerns

- **Config / secrets**: `pydantic-settings`; `.env`; **per-provider auth via env** — `ANTHROPIC_API_KEY` (or an `ant` profile), `OPENAI_API_KEY`, `DEEPSEEK_API_KEY` — never hardcode keys. Provider + model ids live in config (`EXTRACT_PROVIDER`/`EXTRACT_MODEL`, `VERIFY_PROVIDER`/`VERIFY_MODEL`) so they are swappable without code edits (Anthropic is the default).
- **Anti-fake-precision (enforced in code, not just docs)**: no API field or DB column ever stores a combined confidence number. `source_rank` and `directness_rank` are two independent ordinal sort keys. UI shows label + reason only (design §7.3, §14.3).
- **Boundary enforcement (design §3 IN/OUT)**: financials are used only for **cross-stage comparison**; there are no per-company fundamental endpoints. A review checklist item guards against scope creep into Layers 3–5.
- **Evidence is mandatory (design §5.1, §9.2)**: a `fact`-layer edge cannot be written without a bound excerpt; the LLM never writes `confirmed` directly (design §5.3).
- **Testing**: pytest for deterministic units (parsing/resolution/analytics); contract tests for Pydantic LLM schemas; a recorded-fixture pipeline test so prompt regressions surface. See `08-evaluation-and-verification.md`.
