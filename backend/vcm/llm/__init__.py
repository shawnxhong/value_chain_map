"""Provider-pluggable LLM wrapper: structured output, caching, retries (plan/02).

Extraction and verification run on a configurable provider — Anthropic (default), OpenAI,
or DeepSeek — behind one interface. Both return Pydantic contracts; SDK errors surface as
the typed ``LLMError`` hierarchy and usage is normalized to ``LLMUsage``.
"""

from vcm.llm.base import (
    DEFAULT_MAX_TOKENS,
    Effort,
    LLMResult,
    LLMUsage,
    ParseRequest,
    StructuredLLM,
)
from vcm.llm.calls import extract_edges, verify_edge
from vcm.llm.client import get_client
from vcm.llm.errors import (
    LLMAuthError,
    LLMBadRequestError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMRefusalError,
    LLMServiceError,
)
from vcm.llm.registry import get_provider

__all__ = [
    "DEFAULT_MAX_TOKENS",
    "Effort",
    "LLMResult",
    "LLMUsage",
    "ParseRequest",
    "StructuredLLM",
    "extract_edges",
    "verify_edge",
    "get_client",
    "get_provider",
    "LLMError",
    "LLMAuthError",
    "LLMBadRequestError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "LLMRefusalError",
    "LLMServiceError",
]
