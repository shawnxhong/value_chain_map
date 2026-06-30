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
