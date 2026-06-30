# 06 — Phase 1: HBM→packaging→GPU MVP (3–6 weeks)

> Goal: a usable single sub-chain. Implements design §13, §14, §19 Phase 1.

**Sub-chain**: `HBM -> advanced packaging (CoWoS) -> GPU -> AI server -> hyperscaler` (design §13.1). Target ~30 nodes + stages, 200–500 candidate edges. Chosen because its technology migrations (HBM3E->HBM4, CoWoS capacity, pluggable->CPO) and bottlenecks (HBM, advanced-packaging expansion lead times) are typical and best demonstrate the dynamic modeling.

## Task checklist

1. **Migration `0002`**: add `financials`, `profile_cards`; extend `nodes.attributes` (stage `expansion_lead_time`, `concentration`, product `s_curve_stage`); add `companies` investability columns.
2. **Seed `seeds/hbm_subchain.yaml`**: companies, value-chain stages, `BELONGS_TO_STAGE` edges, investability classification per company.
3. **XBRL ingest -> `financials`**: gross margin, op margin, ROIC, FCF margin for the ~30 companies (cross-stage comparison only).
4. **Batch ingest + run**: manual transcripts/decks + 10-Ks; run the pipeline at volume, adopting the **Batches API** (50% cost) for the extraction pass.
5. **Resolution v1**: alias/CIK master + **anonymous-customer nodes** (ASC 280) with the layer rules from `02-pipeline-and-llm.md`.
6. **Analytics**: NetworkX builder; profit-pool ranking + heatmap; bottleneck & weak-link checklists (hit-count + linked excerpts); tech-migration computation.
7. **Profile cards**: generator + `GET /api/cards`; `tier` adjudication + `tier_rationale`.
8. **Frontend**: all eight design §15 views incl. profit-pool coloring, tech-migration, exclusion highlight; profile-card panel; staleness indicators; full review console.
9. **Eval harness (`eval/`)**: hand-label 20–30 gold edges in `seeds/gold_edges.yaml`; compute precision / recall / faithfulness / layer-correctness; run on every prompt change.

## Definition of Done  (= design §4.3 success)

For the HBM sub-chain, the tool answers the five design questions (§14.2) **with traceable evidence**:
1. NVDA's AI-GPU upstream and downstream;
2. where AI-datacenter capex profit settles;
3. which companies an HBM bottleneck affects;
4. which companies are the weak manufacturing links;
5. whether a company has run ahead of its value-chain strength.

And it produces:
- a profit-pool heatmap,
- a bottleneck / weak-link list (with the `structurally_excluded` shortlist),
- a tech-migration view,
- a Structural Profile Card per company with a `tier`,

with gold-set precision/recall **measured and reported**.
