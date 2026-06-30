# 01 — Data model (PostgreSQL)

> Implements design §7 (concept model), §5.2 (profile card), §7.5 (four layers). Single physical DB.

## Staging vs production: a decision

Design §5.3 calls for separating the staging graph from the production graph. **This plan implements that separation as a `status` field + access layer, not as separate physical tables.**

- production graph = rows where `status = 'confirmed'`
- staging graph = rows where `status = 'candidate'`

Rationale: at 50–500 edges, status-filtered views provide review / diff / rollback without duplicating storage. Recorded as an explicit decision so a later physical split is a known, isolated change (it would touch only `graph/` + a migration).

---

## Tables (Alembic migration `0001_init`)

Column sketches — types refined during implementation.

### `nodes`
Generic node; type-specific fields live in `attributes`.
```
id          uuid pk
node_type   enum(company | value_chain_stage | product | technology | end_market)
canonical_name text
chain       text null            -- sub-chain tag, e.g. "ai_datacenter/hbm"
attributes  jsonb                -- stage: expansion_lead_time, concentration; product: s_curve_stage; ...
created_at, updated_at
```

### `companies`  (identity layer, 1:1 with a `company` node — design §7.5 Layer 0, §5.2 investability)
```
node_id              uuid pk fk -> nodes.id
ticker               text
cik                  text
exchange             text
aliases              text[]
investability_status enum(direct_us_listed | adr | foreign_listed | private | segment_inside_large_company | no_clean_vehicle)
investable_ticker    text null
vehicle_purity       enum(high | medium | low | unclear)
```
Indexed columns (ticker, cik, aliases) because entity resolution + investability filtering query them.

### `edges`  (design §7.3, Edge schema v0.3)
```
id               uuid pk
relationship_type enum(SUPPLIES_TO | BELONGS_TO_STAGE | SERVES_MARKET | PRODUCES | COMPETES_WITH | MIGRATES_TO)
source_node_id   uuid fk -> nodes.id
target_node_id   uuid fk -> nodes.id
layer            enum(fact | estimate | inference | thesis)
confidence_label enum(high | medium | low)
confidence_reason text
source_rank      int                 -- ordinal: SEC_filing=5, deck=4, transcript=4, press=3, news=2, low_quality_web=1
directness_rank  int                 -- ordinal: explicitly_named=5, anonymous_but_quantified=4, strongly_implied=3, weakly_implied=2, speculative=1
payer_node_id    uuid null fk -> nodes.id   -- economic_direction (SUPPLIES_TO only)
receiver_node_id uuid null fk -> nodes.id
payment_type     enum(capex | opex | component_cost | service_fee | license_fee | revenue_share | manufacturing_service_fee | unknown)
as_of_date       date                -- evidence publication date; drives staleness
status           enum(candidate | confirmed | deprecated | rejected)
concentration_pct text null          -- e.g. "23%"
created_by       enum(llm_agent | human | import)
chain            text
notes            text
created_at, updated_at
```
**Guardrails (enforced in schema / code):**
- `source_rank` and `directness_rank` are **two independent ordinal sort keys — never combined into a single score** (design §7.3 guardrail).
- `economic_direction` is **required only for `SUPPLIES_TO`**. A CHECK constraint enforces `payer_node_id` / `receiver_node_id` present iff `relationship_type = 'SUPPLIES_TO'` (design §7.2, §16 decision 6).

### `evidence`  (design §7.4)
```
id               uuid pk
source_type      enum(SEC_filing | transcript | presentation | press | news)
title            text
publisher        text null
published_at     timestamptz
retrieved_at     timestamptz
url              text null
accession_number text null
page             int null
section          text null
excerpt          text
excerpt_hash     text
extraction_method enum(rule | llm | human | imported)
```

### `edge_evidence`  (M:N)
```
edge_id     uuid fk -> edges.id
evidence_id uuid fk -> evidence.id
primary key (edge_id, evidence_id)
```
One edge cites many excerpts; one excerpt can support many edges.

### `documents`
```
id          uuid pk
source_type enum(...)
title       text
publisher   text null
published_at timestamptz
retrieved_at timestamptz
url | accession_number  text null
storage_path text       -- raw file in object store (local FS / MinIO)
sha256      text
```

### `chunks`
```
id          uuid pk
document_id uuid fk -> documents.id
ordinal     int
text        text
char_start, char_end int
token_count int
embedding   vector null   -- pgvector, Phase 1 (hybrid retrieval)
```

### `financials`  (XBRL facts; profit-pool comparison only — design §10.1)
```
id        uuid pk
node_id   uuid fk -> nodes.id
metric    enum(gross_margin | op_margin | roic | fcf_margin)
period    text          -- e.g. "FY2025"
value     numeric
source_doc_id uuid fk -> documents.id
```

### `profile_cards`  (generated, regeneratable — design §5.2)
```
id          uuid pk
node_id     uuid fk -> nodes.id
chain       text
as_of_date  date
tier        enum(consider | watch | structurally_excluded)   -- the single adjudicating field
payload     jsonb        -- full StructuralProfileCard (see 03-analytics-and-cards.md)
generated_at timestamptz
```
`payload` carries the design §5.2 fields tagged `[必填]/[尽力]/[设计]`; the MVP fills only the required (`[必填]`) ones.

### `audit_log`  (review traceability + rollback — design §16 decision 10)
```
id          uuid pk
entity_type enum(edge | node | card)
entity_id   uuid
from_state  text
to_state    text
actor       text          -- human id or "llm_agent"/"import"
reason      text
at          timestamptz
```

---

## Pydantic contracts (`backend/vcm/models/`)

One definition per concept, reused by both the API and the LLM structured-output calls:

- **`CandidateEdge`** — LLM extraction output (one per candidate relationship). Fields mirror `edges` minus DB-managed ones, plus an inline `excerpt`. Used as the `output_format` for the Sonnet extraction call.
- **`EdgeVerdict`** — LLM verification output: `supported: bool`, `correct_layer`, `correct_confidence_label`, `reason`. Used as the `output_format` for the Opus verify call.
- **`Edge`, `Evidence`, `Node`, `Company`** — domain models mirroring the tables.
- **`StructuralProfileCard`** — the Layer-3/4/5 handoff contract (full shape in `03-analytics-and-cards.md`).

These contracts are the typed boundary of the system; see `02-pipeline-and-llm.md` for how the LLM layer consumes them.
