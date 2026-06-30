"""Verification step (plan/02 §9.1): check one candidate edge against its chunk.

Formats the candidate into a per-edge claim (the varying question that rides on the cached
chunk prefix) and runs the verify model, which can confirm, downgrade the layer/confidence,
or reject. Thin wrapper over ``vcm.llm.verify_edge``.
"""

from __future__ import annotations

from dataclasses import dataclass

from vcm.llm import LLMUsage, StructuredLLM, verify_edge
from vcm.models import CandidateEdge, EdgeVerdict
from vcm.models.enums import LLMProvider


@dataclass(frozen=True)
class VerificationResult:
    verdict: EdgeVerdict
    usage: LLMUsage
    provider: str
    model: str


def format_claim(candidate: CandidateEdge) -> str:
    """Render a candidate edge as the per-edge claim the verifier judges against the chunk."""
    parts = [
        f"Candidate relationship: {candidate.source} "
        f"--{candidate.relationship_type.value}--> {candidate.target}.",
        f"Asserted layer: {candidate.layer.value}. "
        f"Asserted confidence: {candidate.confidence_label.value}.",
    ]
    ed = candidate.economic_direction
    if ed is not None and ed.payer and ed.receiver:
        parts.append(
            f"Economic direction: {ed.payer} pays {ed.receiver} ({ed.payment_type.value})."
        )
    if candidate.concentration_pct:
        parts.append(f"Concentration disclosed: {candidate.concentration_pct}.")
    parts.append(f'Supporting excerpt: "{candidate.excerpt}"')
    return " ".join(parts)


def verify_candidate(
    chunk_text: str,
    candidate: CandidateEdge,
    *,
    provider: LLMProvider | StructuredLLM | None = None,
    model: str | None = None,
) -> VerificationResult:
    result = verify_edge(chunk_text, format_claim(candidate), provider=provider, model=model)
    return VerificationResult(
        verdict=result.parsed,
        usage=result.usage,
        provider=result.provider,
        model=result.model,
    )
