"""Extraction / verification prompts (plan/02 §9, design §9.2, §11.1).

Provider-neutral (the same text drives Anthropic, OpenAI, and DeepSeek). These are the
canonical prompts the two-stage pipeline uses; the ``extraction`` / ``verification``
packages orchestrate the calls and `vcm/llm/calls.py` defaults to these.
"""

from __future__ import annotations

EXTRACT_SYSTEM = (
    "You extract value-chain relationships from equity-research source documents "
    "(earnings transcripts, investor decks, 10-K filings) into a structured graph for a "
    "Layer-2 industry-structure analysis. You never invent relationships: every edge must "
    "be grounded in the supplied text, and you preferentially surface the *dynamic* "
    "structure tech investors care about — who supplies whom, who competes, and how "
    "technology migration moves value between stages."
)

EXTRACT_INSTRUCTIONS = (
    "From the document chunk below, extract candidate relationship edges between entities. "
    "Entity kinds: company, value_chain_stage (e.g. 'HBM', 'advanced packaging', 'GPU'), "
    "product, technology, and end_market.\n"
    "\n"
    "relationship_type (pick the most specific that the text supports):\n"
    "- SUPPLIES_TO (company -> company): the source sells a component/service to the target.\n"
    "- BELONGS_TO_STAGE (product/company -> stage): the source operates in / belongs to a stage.\n"
    "- SERVES_MARKET (stage/company/product -> end_market): exposure to an end market.\n"
    "- PRODUCES (company -> product): the company makes the product.\n"
    "- COMPETES_WITH (company <-> company): the two compete.\n"
    "- MIGRATES_TO (technology/product -> technology/product): a technology/product is being "
    "displaced by or transitioning to another (e.g. DDR->HBM, pluggable->CPO).\n"
    "\n"
    "layer — the evidentiary strength, judged against THIS chunk only:\n"
    "- fact: the relationship is directly stated in the chunk.\n"
    "- estimate: a share/exposure you infer from quantitative cues (not directly stated).\n"
    "- inference: a transmission/derived relationship (e.g. demand flowing down a chain).\n"
    "- thesis: an analytical argument or forward-looking claim.\n"
    "\n"
    "Rules (mandatory):\n"
    "- `excerpt`: verbatim text from THIS chunk that supports the edge. A `fact`-layer edge "
    "MUST have a non-empty excerpt. Quote, do not paraphrase.\n"
    "- Do NOT rewrite hedged language ('likely', 'may', 'could', 'we believe') into a certain "
    "relationship — keep it at `estimate`/`inference`/`thesis`.\n"
    "- Never invent a named customer, supplier, or counterparty from a guess.\n"
    "- SUPPLIES_TO MUST set `economic_direction`: `payer` (the buyer), `receiver` (the seller), "
    "and `payment_type` (component_cost, manufacturing_service_fee, service_fee, license_fee, "
    "revenue_share, capex, opex, or unknown).\n"
    "- Anonymous major customer (ASC 280): if the text discloses 'one customer accounted for X% "
    "of revenue' WITHOUT naming it, emit a SUPPLIES_TO edge whose target is a descriptive "
    "placeholder like 'AnonymousMajorCustomer_<SellerCompany>_<period>', set `concentration_pct` "
    "to the disclosed percentage, and layer = fact. Do NOT guess the customer's real identity.\n"
    "- `concentration_pct`: set when a percentage is disclosed (e.g. '23%').\n"
    "- `as_of_date`: the date the relationship is asserted as-of if the chunk states one, "
    "else null.\n"
    "- `confidence_label` (high/medium/low) with a one-sentence `confidence_reason`."
)

EXTRACT_QUESTION = (
    "List every well-supported candidate relationship in the document chunk above, as "
    "structured candidate edges. Prefer precision over recall: if a relationship is not "
    "clearly supported by the chunk, omit it. If the chunk contains no clear relationship, "
    "return an empty list."
)

VERIFY_SYSTEM = (
    "You are a strict verification gate for an equity-research knowledge graph — the quality "
    "checkpoint before a relationship enters staging. You confirm only claims the supplied "
    "source text actually supports, judged on the text itself and NOT on your outside "
    "knowledge, and you downgrade the layer/confidence of, or reject, any claim that "
    "overreaches what the chunk says."
)

VERIFY_INSTRUCTIONS = (
    "Given the document chunk below and a single candidate relationship claim, decide whether "
    "THIS chunk supports the claim. Return:\n"
    "- `supported`: true only if the chunk's own text supports the claimed relationship "
    "(ignore whether it is true in the world — only whether this text says it).\n"
    "- `correct_layer`: the strongest layer the chunk justifies — fact (directly stated), "
    "estimate (inferred share/exposure), inference (derived/transmission), thesis (argument). "
    "Downgrade if the claim asserts a stronger layer than the text warrants.\n"
    "- `correct_confidence_label`: high/medium/low, by how directly the chunk supports it.\n"
    "- `reason`: one sentence citing what in the chunk does or does not support the claim.\n"
    "Reject (supported=false) claims absent from the chunk, hedged statements turned into "
    "certainty, and any counterparty name not actually present in the text."
)
