"""Extraction step (plan/02 §9.1): one chunk -> candidate edges via the extract model.

Thin domain wrapper over ``vcm.llm.extract_edges`` (which defaults to the canonical
extraction prompt in ``vcm.llm.prompts``). Keeps the pipeline decoupled from the LLM
mechanism and lets a provider/model be overridden per call (and a fake injected in tests).
"""

from __future__ import annotations

from dataclasses import dataclass

from vcm.llm import LLMUsage, StructuredLLM, extract_edges
from vcm.models import CandidateEdge
from vcm.models.enums import LLMProvider


@dataclass(frozen=True)
class ExtractionResult:
    candidates: list[CandidateEdge]
    usage: LLMUsage
    provider: str
    model: str


def extract_candidates(
    chunk_text: str,
    *,
    provider: LLMProvider | StructuredLLM | None = None,
    model: str | None = None,
) -> ExtractionResult:
    result = extract_edges(chunk_text, provider=provider, model=model)
    return ExtractionResult(
        candidates=result.parsed.candidate_edges,
        usage=result.usage,
        provider=result.provider,
        model=result.model,
    )
