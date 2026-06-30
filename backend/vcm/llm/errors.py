"""Typed errors for the LLM layer (plan/02 — "most-specific-first typed-exception chain").

``vcm.llm`` wraps the Anthropic SDK's exceptions in this small hierarchy so callers
classify failures by *kind* (retryable rate-limit / service vs. terminal bad-request /
auth / refusal) without string-matching SDK messages. The SDK still does the actual
exponential-backoff retries on 429/5xx/connection errors before these surface.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base for all ``vcm.llm`` failures; carries provider/model and (if available) request id."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.request_id = request_id


class LLMConnectionError(LLMError):
    """Network failure before any response (retryable; SDK already retried)."""


class LLMRateLimitError(LLMError):
    """429 — rate limited (retryable; SDK already backed off)."""


class LLMAuthError(LLMError):
    """401/403 — missing or insufficient credentials (not retryable)."""


class LLMBadRequestError(LLMError):
    """400/404 — malformed request or unknown model id (not retryable)."""


class LLMServiceError(LLMError):
    """Other non-2xx response (5xx / overloaded) after retries were exhausted."""


class LLMRefusalError(LLMError):
    """Model returned ``stop_reason='refusal'`` or produced no parseable output."""
