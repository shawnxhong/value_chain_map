# 08 — Evaluation, testing & end-to-end verification

> Implements design §14 (data quality & evaluation) plus the cross-cutting testing strategy.

## Evaluation (first-class, not an afterthought — design §14.2)

- **Gold set**: 20–30 hand-labeled relationships for the HBM sub-chain in `seeds/gold_edges.yaml`, landing in Phase 1.
- **Metrics** (`backend/vcm/eval/`): precision, recall, faithfulness (is the extracted relationship supported by its excerpt?), entity-resolution accuracy, layer-correctness (fact/estimate/inference/thesis assigned right), temporal-correctness.
- **Gate**: the eval runs on **every prompt change** — without it there's no way to tell if extraction is improving or regressing. Run via `python -m vcm.eval`.
- **Cross-provider comparison**: the same gold-set eval can be run per provider (Anthropic / OpenAI / DeepSeek) to compare precision / recall / faithfulness and pick the extract/verify provider per role. Edge provenance (`provider:model`, see `01-data-model.md`) ties each result back to who produced it.

## Confidence labels (de-formularized, sortable — design §14.3)

- **UI shows**: discrete `high / medium / low` + a one-line `confidence_reason`.
- **Internally**: `source_rank` (source type) and `directness_rank` (statement directness) as **two independent ordinals**, used only for sorting/filtering. **Never combined into a single number** — this is enforced in code (no such column or field exists).

## Staleness management (design §14.4)

Every edge carries `as_of_date`. The UI shows "last verified N months ago" and greys edges past a threshold for re-check. Acted on in Phase 2's monitor/diff workflow.

## Testing strategy

- **Deterministic units** (pytest): parsing, entity resolution, analytics (checklist hit-counts, profit-pool ranking).
- **Contract tests**: the Pydantic LLM schemas (`CandidateEdge`, `EdgeVerdict`, `StructuralProfileCard`) validate against representative payloads.
- **Recorded-fixture pipeline test**: a cassette of one chunk -> expected candidate edges, so prompt regressions surface without live API cost.
- **Invariant test**: a `fact` edge with no `edge_evidence` row cannot be written.
- **Frontend**: light component tests in the MVP.

## End-to-end verification

### Phase 0
1. `docker compose up`.
2. `POST /api/pipeline/ingest` a sample 10-K and a transcript.
3. `POST /api/pipeline/run`.
4. Open the frontend, confirm an edge in the review console, click it on the graph, read its excerpt.
5. Confirm the no-evidence-fact-edge invariant test passes.

### Phase 1
1. Load `seeds/hbm_subchain.yaml`.
2. Ingest the curated doc set; run the pipeline (batch).
3. Open each design §15 view.
4. Open three profile cards; confirm `tier` + `tier_rationale` + evidence are present.
5. `python -m vcm.eval` prints precision/recall against `gold_edges.yaml`.

### LLM checks
- Smoke test: the extraction call returns a valid `CandidateEdgeList`; the verify call returns a valid `EdgeVerdict` — on the **configured provider + model** (default `claude-sonnet-4-6` / `claude-opus-4-8`; with reasoning where supported). Opt-in per provider via its key env var (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`).
- Caching check: the normalized `cached_input_tokens > 0` on a same-provider, same-prefix second call (maps to `cache_read_input_tokens` / `prompt_tokens_details.cached_tokens` / `prompt_cache_hit_tokens` — see `02-pipeline-and-llm.md`).
