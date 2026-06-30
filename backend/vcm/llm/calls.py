"""Extraction and verification calls — provider-neutral (plan/02).

`extract_edges` / `verify_edge` are the public entry points. They build a `ParseRequest`
and dispatch to the configured provider (Anthropic by default; OpenAI/DeepSeek per role
via config), so callers never see an SDK. The prompts live in `prompts.py`; the
per-provider mechanics live in `providers/`.
"""

from __future__ import annotations

from vcm.config import get_settings
from vcm.llm.base import DEFAULT_MAX_TOKENS, Effort, LLMResult, ParseRequest, StructuredLLM
from vcm.llm.prompts import (
    EXTRACT_INSTRUCTIONS,
    EXTRACT_QUESTION,
    EXTRACT_SYSTEM,
    VERIFY_INSTRUCTIONS,
    VERIFY_SYSTEM,
)
from vcm.llm.registry import get_provider
from vcm.models import CandidateEdgeList, EdgeVerdict
from vcm.models.enums import LLMProvider

_CHUNK_HEADER = "\n\n--- DOCUMENT CHUNK ---\n"


def _resolve(provider: LLMProvider | StructuredLLM | None, default: LLMProvider) -> StructuredLLM:
    """Pick the provider impl: config default, a named provider, or an injected impl (tests)."""
    if provider is None:
        return get_provider(default)
    if isinstance(provider, LLMProvider):
        return get_provider(provider)
    return provider


def extract_edges(
    chunk: str,
    *,
    provider: LLMProvider | StructuredLLM | None = None,
    model: str | None = None,
    instructions: str = EXTRACT_INSTRUCTIONS,
    system: str = EXTRACT_SYSTEM,
    question: str = EXTRACT_QUESTION,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> LLMResult[CandidateEdgeList]:
    """Extract candidate edges from one chunk (default provider = `extract_provider`)."""
    settings = get_settings()
    impl = _resolve(provider, settings.extract_provider)
    req = ParseRequest(
        model=model or settings.extract_model,
        output_format=CandidateEdgeList,
        system=system,
        cached_prefix=f"{instructions}{_CHUNK_HEADER}{chunk}",
        question=question,
        max_tokens=max_tokens,
        reasoning=False,
    )
    return impl.parse_structured(req)


def verify_edge(
    chunk: str,
    claim: str,
    *,
    provider: LLMProvider | StructuredLLM | None = None,
    model: str | None = None,
    instructions: str = VERIFY_INSTRUCTIONS,
    system: str = VERIFY_SYSTEM,
    effort: Effort = "high",
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> LLMResult[EdgeVerdict]:
    """Verify one candidate ``claim`` against ``chunk`` (default provider = `verify_provider`).

    Requests reasoning + ``effort`` — honored on providers/models that support it
    (Anthropic adaptive thinking, OpenAI/gpt-5 reasoning_effort) and ignored otherwise.
    """
    settings = get_settings()
    impl = _resolve(provider, settings.verify_provider)
    req = ParseRequest(
        model=model or settings.verify_model,
        output_format=EdgeVerdict,
        system=system,
        cached_prefix=f"{instructions}{_CHUNK_HEADER}{chunk}",
        question=claim,
        max_tokens=max_tokens,
        reasoning=True,
        effort=effort,
    )
    return impl.parse_structured(req)
