# 04 — API & Frontend

> Implements design §17 (API, trimmed to MVP) and §15 (UI). Interactive Cytoscape UI from Phase 0.

## API (`backend/vcm/api/`, FastAPI)

MVP surface (full design §17 is broader; deferred routes land in Phase 2):

### Graph
- `GET /api/graph/chain/{chain}` — nodes + edges for a sub-chain. Query filters: `layer`, `status`, `confidence`.
- `GET /api/graph/company/{ticker}/upstream?depth=` and `.../downstream?depth=`

### Evidence
- `GET /api/evidence/{edge_id}` — excerpts + provenance for an edge.

### Cards
- `GET /api/cards/{ticker}` — one Structural Profile Card.
- `GET /api/cards?chain=` — all cards for a chain (the shortlist).

### Analytics
- `GET /api/analytics/profit-pool?chain=`
- `GET /api/analytics/bottleneck?chain=`
- `GET /api/analytics/weak-link?chain=`

### Pipeline
- `POST /api/pipeline/ingest` — upload/fetch a document.
- `POST /api/pipeline/run` — run extract + verify on a document (writes `candidate` edges).

### Review
- `GET /api/review/candidates` — the staging queue.
- `POST /api/review/edge/{id}/confirm` | `/reject` | `/edit` — status transitions (each writes `audit_log`).

All responses are typed by the Pydantic domain models (`01-data-model.md`).

---

## Frontend (`frontend/`, React + Vite + TypeScript + Cytoscape.js)

Interactive from Phase 0; full view set lands in Phase 1.

### Graph canvas
- Pan / zoom; expand a node's up/down-stream.
- **Visual layer distinction (design §7.5)**: `fact` edges solid; `inference` / `thesis` edges dashed/faded so unverified relationships are obviously weaker.

#### Layout / display module

The canvas uses a **layered (Sugiyama) directed layout** so the vertical axis encodes the
value chain — **upstream suppliers at the top, downstream buyers / end-markets at the bottom,
competitors side-by-side on the same row** — instead of a force-directed "hairball".

- **Engine**: ELK `layered` via `cytoscape-elk` (`elk.direction: DOWN`, orthogonal routing,
  generous `nodeNode` / `nodeNodeBetweenLayers` spacing, `separateConnectedComponents` so
  disconnected clusters sit side-by-side). ELK runs on its inlined main-thread worker (no
  `web-worker` shim needed). Chosen over dagre for layer quality/routing; over a React Flow / G6
  rewrite because Cytoscape already carries the edge→evidence + review wiring.
- **Semantic edge classification** (the VCM-specific part, in `frontend/src/graph/layout.ts`):
  - **Flow edges drive vertical ranking** (edge source ranked *above* target): `SUPPLIES_TO`
    (source = seller = upstream → supplier lands above customer with no reversal), `SERVES_MARKET`
    (sinks end-markets to the bottom), `PRODUCES`, `BELONGS_TO_STAGE`.
  - **Lateral edges are excluded from ranking** so their endpoints can share a row:
    `COMPETES_WITH` (mutual, no arrow) and `MIGRATES_TO` (directional tech transition). They still
    render — the layout just runs over the *flow-edge subgraph* (all nodes + flow edges only).
- **Nodes as labeled boxes**: each node is a rounded rectangle with its name inside, colored by
  `node_type` (company / value_chain_stage / product / end_market / technology) — the label *is*
  the node, so text can never overlap other text.
- **Clutter control**: edge relationship labels are shown only on hover/selection; hovering a
  node dims all but its immediate neighborhood.
- **Overlays**: node-type + edge-style legend, an "Upstream ▲ / Downstream ▼" axis hint, and
  Fit / Re-layout controls.
- **Bundle**: the graph engine (cytoscape + elkjs, ~590 kB gzip) is split into its own Vite chunk
  so the initial app JS stays ~50 kB gzip.

### Edge detail panel
On edge click, show: relationship type, layer, `confidence_label` + `confidence_reason`, `economic_direction` (who pays whom), `as_of_date` + staleness indicator ("verified N months ago", greyed past a threshold — design §14.4), `concentration_pct`, evidence excerpts, review status.

### Views (design §15)
1. Company view (company-centric up/down-stream)
2. Stage-chain view (stage-to-stage)
3. End-market view
4. Profit-pool view (color nodes by margin/ROIC)
5. Bottleneck view (highlight bottleneck stages)
6. Weak-link view
7. Tech-migration view (profit moving between stages)
8. Exclusion view (highlight `structurally_excluded`)

### Profile-card panel
Per company: `tier`, `tier_rationale`, `investability`, `open_questions`, `handoff`.

### Review console
Candidate queue -> confirm / reject / edit, wired to the review API.

### Phasing
- **Phase 0**: graph canvas reading `/api/graph/chain`, edge-click -> `/api/evidence`, fact-vs-inference styling, a minimal confirm/reject control.
- **Phase 1**: all eight views, profit-pool coloring, tech-migration, exclusion highlight, profile-card panel, staleness indicators, full review console.
