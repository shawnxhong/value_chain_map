# 05 — Phase 0: Technical validation (1–2 weeks)

> Goal: prove the spine end-to-end. Implements design §19 Phase 0.

**Scope**: 5–10 companies, ~1 document each. Prove `ingest -> parse -> extract (Sonnet) -> verify (Opus) -> Postgres -> Cytoscape -> click-edge-sees-evidence`.

## Task checklist (rough order)

1. **Scaffold** the monorepo: `backend/pyproject.toml`, `frontend/` (Vite + React + TS), `infra/docker-compose.yml` (postgres+pgvector, backend, frontend), `infra/.env.example`, `backend/vcm/config.py` settings loader.
2. **Migration `0001_init`** (Alembic): `nodes, companies, edges, evidence, edge_evidence, documents, chunks, audit_log`. Pydantic contracts in `backend/vcm/models/` (`CandidateEdge`, `EdgeVerdict`, `Edge`, `Evidence`, `Node`, `Company`).
3. **`llm/` wrapper**: Anthropic client, structured output, prompt caching, retry, model ids from config. Smoke test one Sonnet call and one Opus call.
4. **Ingestion**: manual PDF/text upload + one SEC EDGAR 10-K fetch. Docling/Unstructured parse -> chunks (persist `documents`, `chunks`).
5. **Extraction + verification**: extraction prompt + `CandidateEdge` schema (Sonnet); verification prompt + `EdgeVerdict` (Opus, adaptive thinking). Wire `POST /api/pipeline/run`.
6. **Resolution v0 + evidence binding**: exact ticker/alias resolution; bind excerpts; write edges `status=candidate`. Enforce: a `fact` edge with no `edge_evidence` row is rejected at write time.
7. **Review endpoint (minimal)**: confirm / reject + `audit_log`.
8. **Frontend**: Cytoscape canvas reading `/api/graph/chain`; edge-click -> `/api/evidence`; fact-vs-inference edge styling.
9. **Seed & run**: 5–10 companies; run the pipeline on their docs; manually confirm a handful of edges.

## Definition of Done

From a clean `docker compose up`:
- ingest one real 10-K **and** one transcript,
- run the pipeline,
- confirm >=1 edge in the review UI,
- click that edge in the graph and read its source excerpt.

Constraints that must hold:
- extraction uses `claude-sonnet-4-6`, verification uses `claude-opus-4-8`, both via structured output;
- no `fact` edge exists without a bound excerpt (assert this in a test);
- `source_rank` / `directness_rank` are stored as separate ordinals, with no combined score anywhere.
