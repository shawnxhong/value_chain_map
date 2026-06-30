# 02 — Pipeline & LLM layer

> Implements design §8.3 (data flow), §9 (LLM use, de-agented), §11 (data sources), §11.1 (anonymous customers).

## LLM layer (`backend/vcm/llm/`)

Anthropic SDK (`anthropic`), structured output via Pydantic. Auth resolves from env or an `ant` profile — `Anthropic()` zero-arg picks up `ANTHROPIC_API_KEY` or an `ant auth login` profile. **Never hardcode keys.** Model ids come from `config.py` (`EXTRACT_MODEL="claude-sonnet-4-6"`, `VERIFY_MODEL="claude-opus-4-8"`).

### Extraction — `claude-sonnet-4-6`
- Call: `client.messages.parse(model=EXTRACT_MODEL, output_format=CandidateEdgeList, ...)` (Pydantic) or equivalently `output_config={"format": {"type": "json_schema", "schema": ...}}`.
- Input: one chunk + stable schema/instructions.
- Output: candidate edges, each with `relationship_type`, `layer`, inline `excerpt`, `confidence_label`, `confidence_reason`, `economic_direction` (SUPPLIES_TO only), `as_of_date`.
- Enforces design §9.2 prohibitions in the prompt: no `fact` edge without an excerpt; never rewrite "likely / may / could" into a certain relationship; never invent a named customer from a guess.

### Verification — `claude-opus-4-8`
- Call: `thinking={"type": "adaptive"}` + `output_config={"effort": "high"}`, structured `EdgeVerdict` output.
- For each candidate edge, checks the claim against its own excerpt and returns `supported`, the `correct_layer`, the `correct_confidence_label`, and a `reason`. Can downgrade layer/label or reject. This is the quality gate before anything reaches staging.
- Adaptive thinking + structured output are compatible.

### Cost & resilience
- **Prompt caching**: cache the chunk + stable instruction prefix as the cached prefix; vary the per-edge question. Both prompts re-read the same chunk, so the chunk is cached once and read by extraction and verification. Verify `usage.cache_read_input_tokens > 0` in a smoke test.
- **Batches API** (Phase 1, 50% cost): bulk extraction across many chunks is latency-tolerant — submit as a batch, key results by `custom_id`, never by position.
- **Retries / errors**: SDK auto-retries 429/5xx; wrap calls with a most-specific-first typed-exception chain. Stream when `max_tokens` is large.

---

## Pipeline (deterministic — design §9.1)

```
ingest(doc)
  -> parse / chunk
  -> [per chunk] extract (Sonnet) -> candidate edges
  -> verify (Opus) per edge -> support verdict
  -> entity resolution
  -> evidence binding
  -> write edges status=candidate            (staging graph)
  -> human review (confirm / reject / edit)
  -> status=confirmed                         (production graph)
  -> analytics rebuild (NetworkX) -> profile-card regen
```

No multi-agent orchestration in the MVP (design §9.1): the largest early risk is relationship hallucination, not agent capability. Planner / source-discovery / diff / report-writer agents are deferred to Phase 2+.

### Stage detail

- **Ingestion (`ingestion/`)**: manual upload of transcript / deck / PDF (design §11 P0 constraint — high-quality transcripts are paywalled and formats are unstable, so no auto-crawl in MVP) **plus** SEC EDGAR fetch for 10-K and XBRL company-facts. Raw file -> object store (local FS / MinIO); metadata -> `documents`.
- **Parsing (`parsing/`)**: Docling + Unstructured -> markdown -> chunks (table-aware where possible); hash each chunk; persist `chunks`.
- **Entity resolution (`resolution/`)**: map extracted names -> `nodes` via the ticker/CIK/alias master.
- **Evidence binding (`evidence/`)**: every non-rejected edge must have >=1 `evidence` row with a real excerpt. `fact`-layer edges with no excerpt are blocked at write time (design §5.1, §9.2).
- **Review (`review/`)**: status-transition API + `audit_log`. The LLM never writes `confirmed` directly (design §5.3).
- **Analytics rebuild**: on merge to `confirmed`, rebuild the NetworkX graph for the affected chain and regenerate profile cards (see `03-analytics-and-cards.md`).

---

## Anonymous major customers (design §11.1 — a first-class workflow)

ASC 280 often discloses "one customer accounted for 23% of revenue" **without naming the customer**. This is the most reliable supply-chain signal in a 10-K, so it is modeled explicitly rather than dropped.

- Create an anonymous node, e.g. `AnonymousMajorCustomer_<CompanyX>_FY2025`, with `concentration_pct` on the edge.

| Situation | Layer |
|---|---|
| Filing names the customer | `fact` |
| Filing discloses "Customer A = X%" only | `fact` (customer anonymous) |
| Outside source infers Customer A = some company | `estimate` / `inference` |
| LLM guess | **never enters `fact`** |

Later identity resolution updates the node but **never auto-promotes a guess to `fact`**.

---

## LLM output contract (design §9.2)

```json
{
  "candidate_edges": [{
    "source": "Microsoft",
    "target": "NVIDIA",
    "relationship_type": "SUPPLIES_TO",
    "layer": "inference",
    "excerpt": "Microsoft disclosed AI infrastructure capex growth...",
    "confidence_label": "low",
    "confidence_reason": "MSFT disclosed AI capex growth; direct purchase share from NVDA not disclosed in this document",
    "economic_direction": {"payer": "Microsoft", "receiver": "NVIDIA", "payment_type": "component_cost"},
    "as_of_date": "2026-04-25"
  }]
}
```
Prohibited (rejected by verification or schema): a `fact` edge with no excerpt; reasoning written as fact; rewriting hedged language into certainty; auto-overwriting a human-confirmed edge; discarding prior versions.
