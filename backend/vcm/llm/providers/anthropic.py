"""Anthropic provider — structured output via ``messages.parse`` (plan/02).

Carries the Anthropic-specific knobs: explicit ``cache_control`` on the chunk prefix,
adaptive ``thinking`` when reasoning is requested, and ``output_config.effort``.
"""

from __future__ import annotations

from typing import Any, cast

import anthropic
from pydantic import BaseModel

from vcm.llm.base import LLMResult, LLMUsage, ParseRequest
from vcm.llm.client import get_client
from vcm.llm.errors import (
    LLMAuthError,
    LLMBadRequestError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMRefusalError,
    LLMServiceError,
)

_CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, *, client: anthropic.Anthropic | None = None) -> None:
        self._client = client

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = get_client()
        return self._client

    def _build_kwargs[T: BaseModel](self, req: ParseRequest[T]) -> dict[str, Any]:
        # chunk prefix gets the cache_control breakpoint; the question follows it uncached.
        content = [
            {"type": "text", "text": req.cached_prefix, "cache_control": dict(_CACHE_CONTROL)},
            {"type": "text", "text": req.question},
        ]
        kwargs: dict[str, Any] = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "system": req.system,
            "messages": [{"role": "user", "content": content}],
            "output_format": req.output_format,
        }
        if req.reasoning:
            kwargs["thinking"] = {"type": "adaptive"}
        if req.effort is not None:
            kwargs["output_config"] = {"effort": req.effort}
        return kwargs

    def parse_structured[T: BaseModel](self, req: ParseRequest[T]) -> LLMResult[T]:
        kwargs = self._build_kwargs(req)
        try:
            resp = self.client.messages.parse(**kwargs)
        except anthropic.APIConnectionError as e:  # no HTTP response -> no request_id
            raise LLMConnectionError(str(e), provider=self.name, model=req.model) from e
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(
                str(e), provider=self.name, model=req.model, request_id=e.request_id
            ) from e
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            raise LLMAuthError(
                str(e), provider=self.name, model=req.model, request_id=e.request_id
            ) from e
        except (anthropic.BadRequestError, anthropic.NotFoundError) as e:
            raise LLMBadRequestError(
                str(e), provider=self.name, model=req.model, request_id=e.request_id
            ) from e
        except anthropic.APIStatusError as e:  # remaining 5xx / overloaded
            raise LLMServiceError(
                str(e), provider=self.name, model=req.model, request_id=e.request_id
            ) from e

        if resp.stop_reason == "refusal" or resp.parsed_output is None:
            raise LLMRefusalError(
                f"no parseable output (stop_reason={resp.stop_reason})",
                provider=self.name,
                model=req.model,
                request_id=resp._request_id,
            )

        u = resp.usage
        cache_read = u.cache_read_input_tokens or 0
        cache_creation = getattr(u, "cache_creation_input_tokens", 0) or 0
        usage = LLMUsage(
            input_tokens=(u.input_tokens or 0) + cache_read + cache_creation,
            output_tokens=u.output_tokens or 0,
            cached_input_tokens=cache_read,
        )
        return LLMResult(
            parsed=cast(T, resp.parsed_output),
            usage=usage,
            provider=self.name,
            model=resp.model,
            request_id=resp._request_id,
            finish_reason=resp.stop_reason,
        )
