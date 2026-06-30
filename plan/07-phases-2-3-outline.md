# 07 — Phases 2–3 (outline)

> Lighter roadmap; refine once Phase 1 lands. Implements design §13.4, §18.

## Phase 2 — incremental updates & layer interfaces (6–10 weeks)

Goal: let the graph stay current and wire the toolset's seams.

- **Weekly monitor**: scheduled filings/news ingestion for existing nodes.
- **Graph diff + review alerts**: detect new/changed/deprecated relationships; raise review alerts on high-impact changes.
- **Staleness / deprecation workflow**: act on `as_of_date` — surface "last verified N months ago", grey out and queue stale edges for re-check (design §14.4).
- **`chain_exposure` estimation**: populate the `[尽力]` card field (pure_play vs minor_segment) to flag impure concept exposure.
- **Layer interfaces**:
  - **Input from Layer 1**: a manual "demand tide" global parameter (capex-cycle expansion/contraction, rate environment) injected at the top of the chain (design §5.1).
  - **Output to Layers 3/4/5**: formalize the Structural Profile Card handoff (the `handoff.layer3/4/5` fields) as the toolset's interface contract.
- **Event-impact paths**: trace how an event (e.g. a capex guide-up) propagates along the chain.

## Phase 3 — breadth (10 weeks+)

Goal: more sub-chains and scale.

- **Additional sub-chains**: semiconductor equipment, power/cooling, optical, battery.
- **Multi-chain schema**: support cross-chain themes.
- **Link prediction**: populate the estimate layer with model-suggested relationships (still gated by review).
- **API export**: expose the graph + cards to downstream tools.
- **Graph-DB migration (only if scale demands)**: move `backend/vcm/graph/` from Postgres-rows + NetworkX to Kuzu or Neo4j. Isolated by design to that one package.
- **Multi-user roles**: for a collaboration build (review permissions, audit by actor).
