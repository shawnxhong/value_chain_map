# 02 — Pipeline & LLM layer

> Implements design §8.3 (data flow), §9 (LLM use, de-agented), §11 (data sources), §11.1 (anonymous customers).

## LLM layer (`backend/vcm/llm/`)

**Provider-pluggable.** Extraction and verification each run on a configurable provider —
**Anthropic (default), OpenAI, or DeepSeek** — behind one stable interface, so the deterministic
pipeline (§9.1 below) and all callers stay provider-agnostic. Auth resolves per provider from the
environment at call time (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`); **never
hardcode keys.** Provider + model ids come from `config.py`.

### Provider abstraction

```
vcm/llm/
  base.py            # Provider protocol, ParseRequest[T], neutral LLMUsage
  registry.py        # get_provider(Provider) -> impl, cached
  providers/
    anthropic.py     # messages.parse + cache_control + thinking + effort
    openai_compat.py # OpenAI AND DeepSeek (OpenAI SDK; base_url + structured_mode differ)
  calls.py           # extract_edges / verify_edge — provider-neutral; selects from config
  errors.py          # LLMError hierarchy; maps anthropic.* and openai.*
```

- **`Provider` protocol** — `parse_structured(req: ParseRequest[T]) -> LLMResult[T]`.
- **`ParseRequest[T]`** — `model`, `output_format` (Pydantic), `system`, `cached_prefix` (stable:
  instructions + chunk), `question` (varying), `max_tokens`, `reasoning: bool`, `effort`.
- **`LLMResult[T]`** — `parsed`, `usage: LLMUsage`, `provider`, `model`, `request_id`, `finish_reason`.
- **`LLMUsage`** — neutral `input_tokens` / `output_tokens` / `cached_input_tokens`; each provider's
  native usage is normalized into it (so the caching check is provider-agnostic).
- The **public API is unchanged** — `extract_edges`, `verify_edge`, `LLMResult`, the `LLMError`
  hierarchy. Only the internals fan out to providers.

### Selection (config-driven, per role)

```yaml
extract_provider: anthropic            # default; or openai | deepseek
extract_model:    claude-sonnet-4-6
verify_provider:  anthropic            # default
verify_model:     claude-opus-4-8
deepseek_base_url: https://api.deepseek.com
```
Per-role selection means extract and verify can run on different providers (e.g. extract on
DeepSeek, verify on Anthropic). Keys stay out of config — resolved from env per provider.

### Roles (provider-neutral)

- **Extraction** — one chunk + stable schema/instructions → `CandidateEdgeList`: candidate edges
  with `relationship_type`, `layer`, inline `excerpt`, `confidence_label`, `confidence_reason`,
  `economic_direction` (SUPPLIES_TO only), `as_of_date`. The prompt enforces the design §9.2
  prohibitions: no `fact` edge without an excerpt; never rewrite "likely / may / could" into a
  certain relationship; never invent a named customer from a guess.
- **Verification** — for each candidate, checks the claim against its own excerpt and returns
  `EdgeVerdict` (`supported`, `correct_layer`, `correct_confidence_label`, `reason`); can downgrade
  layer/label or reject. The quality gate before anything reaches staging. Runs with reasoning +
  `effort=high` where the provider supports it.

### Per-provider capability matrix

| Provider | Structured output | Reasoning / effort | Prompt caching | `cached_input_tokens` from | Exceptions |
|---|---|---|---|---|---|
| **Anthropic** (default) | `messages.parse(output_format=…)` | `thinking` adaptive + `output_config.effort` | **explicit** `cache_control` on the prefix | `usage.cache_read_input_tokens` | `anthropic.*` |
| **OpenAI** | `chat.completions.parse(response_format=…)` (json_schema, strict) | `reasoning_effort` (o-series / gpt-5) | **automatic** (prefix ≥ ~1024 tok) | `usage.prompt_tokens_details.cached_tokens` | `openai.*` |
| **DeepSeek** | `chat.completions.create(response_format={"type":"json_object"})` + schema in prompt + `model_validate_json` | optional via `deepseek-reasoner` | **automatic** (context caching) | `usage.prompt_cache_hit_tokens` | `openai.*` (same SDK + `base_url`) |

- **Message shape is already cross-provider-friendly**: stable content first (system +
  instructions + chunk), varying question last. Anthropic marks the breakpoint with `cache_control`;
  OpenAI/DeepSeek auto-cache the same prefix with no marker.
- **DeepSeek has no strict `json_schema`** → JSON-mode + client-side Pydantic validation; a validation
  failure maps to `LLMRefusalError` (optionally one re-ask). Default model `deepseek-chat`;
  `deepseek-reasoner` is optional and its JSON-mode support is the caveat.
- **OpenAI and DeepSeek share one provider class** (the `openai` SDK), differing only by `base_url`,
  key env var, and `structured_mode ∈ {json_schema, json_object}`.
- **Refusals** map uniformly to `LLMRefusalError`: Anthropic `stop_reason='refusal'`, OpenAI
  `message.refusal` / `parsed is None`, DeepSeek JSON-validate failure.

### Cost & resilience
- **Prompt caching**: keep the chunk + stable instructions as the leading prefix and vary the
  per-edge question. Anthropic caches it via an explicit `cache_control` breakpoint; OpenAI and
  DeepSeek auto-cache the prefix. The smoke test asserts the normalized `cached_input_tokens > 0` on a
  same-provider, same-prefix second call. (Caches are model-scoped, so extraction and verification do
  not share one.)
- **Batches API** (Phase 1, 50% cost): bulk extraction is latency-tolerant — submit as a batch, key
  results by `custom_id`, never by position. Anthropic and OpenAI both expose batch APIs; DeepSeek
  does not (fall back to bounded concurrency).
- **Retries / errors**: each SDK auto-retries 429/5xx; calls are wrapped in a most-specific-first
  typed-exception chain that maps `anthropic.*` and `openai.*` into the shared `LLMError` hierarchy.
  Stream when `max_tokens` is large.

> **Dependency / status**: adds `openai>=1.x` to core deps (DeepSeek reuses it; `anthropic` stays).
> The provider split is a planned refactor of the Phase-0 Anthropic-only wrapper — implement it behind
> the unchanged public API, and verify the exact OpenAI-SDK method and usage-field names against the
> installed version first (as was done for the Anthropic SDK).

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
