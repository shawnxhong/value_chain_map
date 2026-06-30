"""OpenAI-compatible provider — serves both OpenAI and DeepSeek (plan/02).

One class, two structured-output strategies (the only real difference, plus base_url /
key / token-param):

* ``json_schema`` (OpenAI): native strict structured outputs via
  ``chat.completions.parse(response_format=<PydanticModel>)`` → ``message.parsed``.
* ``json_object`` (DeepSeek): DeepSeek has no strict json_schema, so we run JSON mode
  (``response_format={"type": "json_object"}``), inject the schema into the system
  prompt, and validate the returned JSON with Pydantic client-side.

Reasoning models (OpenAI o-series / gpt-5) get ``reasoning_effort`` when a reasoning
request asks for it; everything else ignores it. Prompt caching is automatic on both
backends (the stable prefix is sent first), reported via different usage fields.
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal, cast

import openai
from pydantic import BaseModel, ValidationError

from vcm.config import get_settings
from vcm.llm.base import LLMResult, LLMUsage, ParseRequest
from vcm.llm.errors import (
    LLMAuthError,
    LLMBadRequestError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMRefusalError,
    LLMServiceError,
)

StructuredMode = Literal["json_schema", "json_object"]

# OpenAI reasoning_effort accepts low/medium/high; map the wider neutral scale down.
_EFFORT_MAP: dict[str, str] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "high",
    "max": "high",
}
# Model-name prefixes that accept reasoning_effort (OpenAI o-series / gpt-5 family).
_REASONING_PREFIXES = ("o1", "o3", "o4", "o5", "gpt-5")


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        name: str,
        api_key_env: str,
        structured_mode: StructuredMode,
        base_url: str | None = None,
        token_param: str = "max_completion_tokens",
        supports_reasoning_effort: bool = True,
        client: openai.OpenAI | None = None,
    ) -> None:
        self.name = name
        self._api_key_env = api_key_env
        self._structured_mode = structured_mode
        self._base_url = base_url
        self._token_param = token_param
        self._supports_reasoning_effort = supports_reasoning_effort
        self._client = client

    @property
    def client(self) -> openai.OpenAI:
        if self._client is None:
            api_key = os.environ.get(self._api_key_env)
            if not api_key:
                raise LLMAuthError(f"{self._api_key_env} is not set", provider=self.name)
            self._client = openai.OpenAI(
                api_key=api_key,
                base_url=self._base_url,
                max_retries=get_settings().llm_max_retries,
            )
        return self._client

    def _wants_effort[T: BaseModel](self, req: ParseRequest[T]) -> bool:
        return (
            self._supports_reasoning_effort
            and req.reasoning
            and req.effort is not None
            and req.model.lower().startswith(_REASONING_PREFIXES)
        )

    def parse_structured[T: BaseModel](self, req: ParseRequest[T]) -> LLMResult[T]:
        try:
            if self._structured_mode == "json_schema":
                return self._parse_json_schema(req)
            return self._create_json_object(req)
        except openai.APIConnectionError as e:  # no HTTP response -> no request_id
            raise LLMConnectionError(str(e), provider=self.name, model=req.model) from e
        except openai.RateLimitError as e:
            raise LLMRateLimitError(
                str(e), provider=self.name, model=req.model, request_id=e.request_id
            ) from e
        except (openai.AuthenticationError, openai.PermissionDeniedError) as e:
            raise LLMAuthError(
                str(e), provider=self.name, model=req.model, request_id=e.request_id
            ) from e
        except (openai.BadRequestError, openai.NotFoundError) as e:
            raise LLMBadRequestError(
                str(e), provider=self.name, model=req.model, request_id=e.request_id
            ) from e
        except openai.APIStatusError as e:  # remaining 5xx / overloaded
            raise LLMServiceError(
                str(e), provider=self.name, model=req.model, request_id=e.request_id
            ) from e

    # --- json_schema (OpenAI native structured outputs) --------------------- #

    def _parse_json_schema[T: BaseModel](self, req: ParseRequest[T]) -> LLMResult[T]:
        messages = [
            {"role": "system", "content": req.system},
            {"role": "user", "content": req.cached_prefix},
            {"role": "user", "content": req.question},
        ]
        kwargs: dict[str, Any] = {
            "model": req.model,
            "messages": messages,
            "response_format": req.output_format,
            self._token_param: req.max_tokens,
        }
        if self._wants_effort(req):
            kwargs["reasoning_effort"] = _EFFORT_MAP[cast(str, req.effort)]
        completion = self.client.chat.completions.parse(**kwargs)
        choice = completion.choices[0]
        message = choice.message
        if message.refusal:
            raise LLMRefusalError(
                f"model refusal: {message.refusal}",
                provider=self.name,
                model=req.model,
                request_id=getattr(completion, "_request_id", None),
            )
        if message.parsed is None:
            raise LLMRefusalError(
                f"no parseable output (finish_reason={choice.finish_reason})",
                provider=self.name,
                model=req.model,
                request_id=getattr(completion, "_request_id", None),
            )
        return self._result(completion, choice.finish_reason, cast(T, message.parsed), req)

    # --- json_object (DeepSeek JSON mode + client-side validation) ----------- #

    def _create_json_object[T: BaseModel](self, req: ParseRequest[T]) -> LLMResult[T]:
        schema = json.dumps(req.output_format.model_json_schema())
        system = (
            f"{req.system}\n\nReturn a single JSON object that conforms to this JSON "
            f"schema. Output only the JSON object, with no surrounding prose.\n"
            f"JSON schema:\n{schema}"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": req.cached_prefix},
            {"role": "user", "content": req.question},
        ]
        kwargs: dict[str, Any] = {
            "model": req.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            self._token_param: req.max_tokens,
        }
        completion = self.client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        content = choice.message.content or ""
        try:
            parsed = req.output_format.model_validate_json(content)
        except ValidationError as e:
            raise LLMRefusalError(
                f"JSON did not validate against {req.output_format.__name__}: {e}",
                provider=self.name,
                model=req.model,
                request_id=getattr(completion, "_request_id", None),
            ) from e
        return self._result(completion, choice.finish_reason, parsed, req)

    # --- shared result + usage normalization -------------------------------- #

    def _result[T: BaseModel](
        self, completion: Any, finish_reason: str | None, parsed: T, req: ParseRequest[T]
    ) -> LLMResult[T]:
        return LLMResult(
            parsed=parsed,
            usage=_normalize_usage(completion.usage),
            provider=self.name,
            model=completion.model or req.model,
            request_id=getattr(completion, "_request_id", None) or completion.id,
            finish_reason=finish_reason,
        )


def _normalize_usage(usage: Any) -> LLMUsage:
    if usage is None:
        return LLMUsage(input_tokens=0, output_tokens=0, cached_input_tokens=0)
    # OpenAI: prompt_tokens_details.cached_tokens; DeepSeek: prompt_cache_hit_tokens.
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details is not None else None
    if not cached:
        cached = getattr(usage, "prompt_cache_hit_tokens", 0)
    return LLMUsage(
        input_tokens=usage.prompt_tokens or 0,
        output_tokens=usage.completion_tokens or 0,
        cached_input_tokens=cached or 0,
    )
