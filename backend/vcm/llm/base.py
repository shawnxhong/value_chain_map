"""Provider-neutral types for the LLM layer (plan/02 §Provider abstraction).

These let `calls.py` and callers stay provider-agnostic: a `ParseRequest` describes
*what* to ask, a `StructuredLLM` provider knows *how* to ask a given backend, and
`LLMResult` / `LLMUsage` normalize the answer so cross-provider code (e.g. the caching
check) never touches an SDK-specific shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

# effort is provider-neutral here; each provider maps it to its own knob
# (Anthropic output_config.effort, OpenAI reasoning_effort) or ignores it.
Effort = Literal["low", "medium", "high", "xhigh", "max"]

# Non-streaming output cap — above EdgeVerdict / a chunk's edge list (plus reasoning
# tokens) and under the SDKs' ~10-min non-streaming timeout guard.
DEFAULT_MAX_TOKENS = 16000


@dataclass(frozen=True)
class LLMUsage:
    """Normalized token usage. ``input_tokens`` is the total prompt size;
    ``cached_input_tokens`` is the subset served from a prompt cache."""

    input_tokens: int
    output_tokens: int
    cached_input_tokens: int


@dataclass(frozen=True)
class LLMResult[T: BaseModel]:
    """A parsed structured-output response plus the metadata callers care about."""

    parsed: T
    usage: LLMUsage
    provider: str
    model: str
    request_id: str | None
    finish_reason: str | None


@dataclass(frozen=True)
class ParseRequest[T: BaseModel]:
    """One structured-output request, provider-agnostic.

    ``cached_prefix`` (stable instructions + chunk) is sent ahead of the varying
    ``question`` so the prefix caches (explicit on Anthropic, automatic on OpenAI/
    DeepSeek). ``reasoning`` + ``effort`` are honored where the provider/model supports
    them and ignored otherwise.
    """

    model: str
    output_format: type[T]
    system: str
    cached_prefix: str
    question: str
    max_tokens: int = DEFAULT_MAX_TOKENS
    reasoning: bool = False
    effort: Effort | None = None


@runtime_checkable
class StructuredLLM(Protocol):
    """A provider that turns a `ParseRequest` into a validated `LLMResult`."""

    name: str

    def parse_structured[T: BaseModel](self, req: ParseRequest[T]) -> LLMResult[T]: ...
