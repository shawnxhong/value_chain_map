# 03 — Structural analytics & Profile Card

> Implements design §10 (structural scores), §6 (tech-migration), §5.2 (profile card). All scores are **evidence-driven checklists / cross-stage comparisons — never weighted decimals**.

## Analytics (`backend/vcm/analytics/`)

### NetworkX build
Load `status='confirmed'` edges for a `chain` into a `networkx.DiGraph`; cache in memory; rebuild on merge. This is the only place graph algorithms run, so a later move to Kuzu/Neo4j is isolated here.

### Profit pool (design §10.1)
Rank the stages of **one chain** by `financials` (gross margin, op margin, ROIC, FCF margin) plus concentration -> `profit_pool_tier: high | medium | low`. This is a **cross-stage comparison only** — never a per-company fundamental analysis (boundary, design §3). Output feeds a profit-pool heatmap.

### Bottleneck checklist (design §10.2)
Hit-count over six evidence-backed features, each linked to an excerpt:
1. supply-constrained
2. long expansion lead time
3. high concentration
4. downstream explicitly cites a supply constraint
5. no near-term substitute
6. customers pre-pay or sign long-term agreements

Output: `bottleneck_hits N/6` + `bottleneck_status: bottleneck | potential_bottleneck | not_bottleneck | unclear`. Display as `Bottleneck 4/6` + excerpts, **not** `0.71`.

### Weak-link checklist (design §10.3)
Hit-count over six features:
1. low margin
2. squeezed by both upstream and downstream
3. commoditized product
4. price-taker
5. single large customer or single product
6. many substitutes

Output: `weak_link_hits N/6` + `weak_link_status`. This is the primary basis for `tier = structurally_excluded`.

### Tech-migration (design §6 — the differentiator)
From `MIGRATES_TO` edges (carrying `s_curve_stage` and direction), compute "profit moving from stage A to stage B" (e.g. DDR->HBM, pluggable->CPO, air->liquid cooling). Drives the tech-migration view.

### Comparability without fake precision
Sorting/ranking uses structured fields only: `bottleneck_hits`, `weak_link_hits`, `profit_pool_tier`, `confidence_label`, and the two independent ordinal ranks (`source_rank`, then `directness_rank`, lexicographically). **No combined score is ever computed or stored.**

---

## Structural Profile Card (design §5.2 — the Layer-3/4/5 handoff)

The card is the **first core deliverable**. Schema is complete; the **MVP fills only `[必填]` (required) fields**, leaving `[尽力]`/`[设计]` for later so cards don't degrade into a wall of `unknown`. `tier` is the **single adjudicating field**; `bottleneck_status`/`weak_link_status`/`tier_rationale` support and back it — they are not a parallel state machine.

```yaml
StructuralProfileCard:                 # [必填]=MVP required; [尽力]=best-effort; [设计]=schema-only
  ticker: string                       # [必填]
  company_name: string                 # [必填]
  chain: string                        # [必填]
  value_chain_stage: string            # [必填]

  structural_position: string          # [必填] one-line qualitative
  profit_pool_tier: high|medium|low|unclear     # [必填]
  bottleneck_status: bottleneck|potential_bottleneck|not_bottleneck|unclear   # [必填]
  weak_link_status: weak_link|potential_weak_link|not_weak_link|unclear        # [必填]

  key_dependencies:
    upstream: string                   # [必填]
    downstream: string                 # [必填]

  investability:                       # [必填] cheap; converges to US-investable names
    status: direct_us_listed|adr|foreign_listed|private|segment_inside_large_company|no_clean_vehicle
    ticker: string|null
    vehicle_purity: high|medium|low|unclear   # is this ticker a clean vehicle for the node?

  chain_exposure:                      # [尽力] how much of the company's economics is this chain
    exposure_type: pure_play|meaningful_segment|minor_segment|unclear
    estimated_revenue_exposure: unknown|low|medium|high
    evidence_ids: [string]

  tech_migration_risk:                 # [尽力] empty if none
    threat: string
    direction: string                  # which stage profit moves from -> to
    s_curve_stage: early|ramping|mature|unclear
    layer: fact|estimate|inference|thesis

  structural_thesis: string            # [必填] free text
  open_questions: [string]             # [必填] hand off concrete things to verify

  handoff:                             # [必填] free text
    layer3: string                     # what moat depth to verify
    layer4: string                     # what fundamentals to verify
    layer5: string                     # what valuation to watch

  tier: consider|watch|structurally_excluded   # [必填] single adjudicating field
  tier_rationale:                      # [必填] structured backing for tier
    reasons: [string]
    override_conditions: [string]      # e.g. "valuation extreme", "tech-migration beneficiary evidence", "customer mix improves"

  evidence_ids: [string]               # [必填]
  as_of_date: date                     # [必填]
```

### `tier` semantics (design §5.2)
- `consider` — structurally strong; recommend deeper analysis at the next layer.
- `watch` — structurally neutral or has open questions; observe.
- `structurally_excluded` — currently weak position; **low research priority unless the next layer finds strong counter-evidence (extreme cheapness / structural improvement / tech-migration benefit). Not a sell call; not a permanent blacklist.**

### Generator (`analytics/`)
Assembles the card from: graph position (NetworkX) + the three checklists + `financials` + `companies.investability`. Persists to `profile_cards` (regeneratable; carries `as_of_date`). Exposed at `/api/cards/...` (see `04-api-and-frontend.md`).
