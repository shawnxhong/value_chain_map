"""Offline unit tests for the provider-pluggable LLM layer (no network).

Covers the deterministic logic: call wiring (`extract_edges`/`verify_edge` → `ParseRequest`),
each provider's request assembly + usage normalization + refusal + typed-exception mapping,
and the registry. Live behaviour is in `test_llm_smoke.py` (opt-in).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import openai
import pytest

from vcm.config import get_settings
from vcm.llm import (
    LLMAuthError,
    LLMBadRequestError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResult,
    LLMUsage,
    ParseRequest,
    extract_edges,
    verify_edge,
)
from vcm.llm.errors import LLMRefusalError, LLMServiceError
from vcm.llm.providers.anthropic import AnthropicProvider
from vcm.llm.providers.openai_compat import OpenAICompatibleProvider
from vcm.llm.registry import get_provider
from vcm.models import CandidateEdgeList, EdgeVerdict
from vcm.models.enums import ConfidenceLabel, Layer, LLMProvider

_VERDICT = EdgeVerdict(
    supported=True,
    correct_layer=Layer.fact,
    correct_confidence_label=ConfidenceLabel.high,
    reason="supported by the excerpt",
)
_VERDICT_JSON = _VERDICT.model_dump_json()
_REQ = httpx.Request("POST", "https://example.com/v1")


def _parse_req[T](output_format: type[T], **over: Any) -> ParseRequest[T]:
    base: dict[str, Any] = {
        "model": "m",
        "output_format": output_format,
        "system": "SYS",
        "cached_prefix": "INSTRUCTIONS + CHUNK",
        "question": "the question",
    }
    base.update(over)
    return ParseRequest(**base)


# --------------------------------------------------------------------------- #
# Call wiring: extract_edges / verify_edge -> ParseRequest
# --------------------------------------------------------------------------- #


class _RecordingProvider:
    name = "fake"

    def __init__(self) -> None:
        self.req: ParseRequest[Any] | None = None

    def parse_structured(self, req: ParseRequest[Any]) -> LLMResult[Any]:
        self.req = req
        parsed = (
            CandidateEdgeList(candidate_edges=[])
            if req.output_format is CandidateEdgeList
            else _VERDICT
        )
        return LLMResult(
            parsed=parsed,
            usage=LLMUsage(0, 0, 0),
            provider=self.name,
            model=req.model,
            request_id="r",
            finish_reason="stop",
        )


def test_extract_builds_non_reasoning_request() -> None:
    fake = _RecordingProvider()
    extract_edges("some chunk", provider=fake)
    req = fake.req
    assert req is not None
    assert req.output_format is CandidateEdgeList
    assert req.model == get_settings().extract_model
    assert req.reasoning is False
    assert req.effort is None
    assert "DOCUMENT CHUNK" in req.cached_prefix and "some chunk" in req.cached_prefix


def test_verify_builds_reasoning_request_with_effort() -> None:
    fake = _RecordingProvider()
    verify_edge("some chunk", "NVDA SUPPLIES_TO MSFT", provider=fake)
    req = fake.req
    assert req is not None
    assert req.output_format is EdgeVerdict
    assert req.model == get_settings().verify_model
    assert req.reasoning is True
    assert req.effort == "high"
    assert req.question == "NVDA SUPPLIES_TO MSFT"


def test_explicit_model_override() -> None:
    fake = _RecordingProvider()
    extract_edges("c", provider=fake, model="custom-model")
    assert fake.req is not None and fake.req.model == "custom-model"


# --------------------------------------------------------------------------- #
# Anthropic provider
# --------------------------------------------------------------------------- #


class _FakeMessages:
    def __init__(self, *, result: Any = None, exc: BaseException | None = None) -> None:
        self._result = result
        self._exc = exc
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._exc is not None:
            raise self._exc
        return self._result


class _FakeAnthropic:
    def __init__(self, *, result: Any = None, exc: BaseException | None = None) -> None:
        self.messages = _FakeMessages(result=result, exc=exc)


def _anthropic_resp(parsed: Any, *, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        parsed_output=parsed,
        usage=SimpleNamespace(
            input_tokens=10,
            cache_read_input_tokens=20,
            cache_creation_input_tokens=5,
            output_tokens=7,
        ),
        model="claude-x",
        _request_id="req_a",
        stop_reason=stop_reason,
    )


def test_anthropic_builds_cache_thinking_effort_and_normalizes_usage() -> None:
    fake = _FakeAnthropic(result=_anthropic_resp(_VERDICT))
    provider = AnthropicProvider(client=fake)  # type: ignore[arg-type]
    result = provider.parse_structured(_parse_req(EdgeVerdict, reasoning=True, effort="high"))
    sent = fake.messages.calls[0]
    content = sent["messages"][0]["content"]
    assert content[0]["cache_control"] == {"type": "ephemeral"}  # prefix cached
    assert "cache_control" not in content[1]  # varying question not cached
    assert sent["thinking"] == {"type": "adaptive"}
    assert sent["output_config"] == {"effort": "high"}
    assert sent["output_format"] is EdgeVerdict
    # usage: input = uncached + cache_read + cache_creation; cached = cache_read
    assert result.usage == LLMUsage(input_tokens=35, output_tokens=7, cached_input_tokens=20)
    assert result.provider == "anthropic"
    assert result.request_id == "req_a"


def test_anthropic_extract_has_no_thinking_or_effort() -> None:
    fake = _FakeAnthropic(result=_anthropic_resp(CandidateEdgeList(candidate_edges=[])))
    AnthropicProvider(client=fake).parse_structured(_parse_req(CandidateEdgeList))  # type: ignore[arg-type]
    sent = fake.messages.calls[0]
    assert "thinking" not in sent
    assert "output_config" not in sent


def test_anthropic_refusal_raises() -> None:
    fake = _FakeAnthropic(result=_anthropic_resp(None, stop_reason="refusal"))
    with pytest.raises(LLMRefusalError):
        AnthropicProvider(client=fake).parse_structured(_parse_req(EdgeVerdict))  # type: ignore[arg-type]


def _anthropic_status(cls: type[anthropic.APIStatusError], code: int) -> anthropic.APIStatusError:
    resp = httpx.Response(code, request=_REQ, headers={"request-id": "rid"})
    return cls("boom", response=resp, body=None)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (_anthropic_status(anthropic.RateLimitError, 429), LLMRateLimitError),
        (_anthropic_status(anthropic.AuthenticationError, 401), LLMAuthError),
        (_anthropic_status(anthropic.BadRequestError, 400), LLMBadRequestError),
        (_anthropic_status(anthropic.NotFoundError, 404), LLMBadRequestError),
        (_anthropic_status(anthropic.InternalServerError, 500), LLMServiceError),
        (anthropic.APIConnectionError(message="x", request=_REQ), LLMConnectionError),
    ],
)
def test_anthropic_exception_mapping(exc: BaseException, expected: type[Exception]) -> None:
    fake = _FakeAnthropic(exc=exc)
    with pytest.raises(expected) as ei:
        AnthropicProvider(client=fake).parse_structured(_parse_req(EdgeVerdict))  # type: ignore[arg-type]
    assert ei.value.provider == "anthropic"  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# OpenAI-compatible provider — json_schema (OpenAI) and json_object (DeepSeek)
# --------------------------------------------------------------------------- #


class _FakeCompletions:
    def __init__(self, *, result: Any = None, exc: BaseException | None = None) -> None:
        self._result = result
        self._exc = exc
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.calls.append(("parse", kwargs))
        if self._exc is not None:
            raise self._exc
        return self._result

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(("create", kwargs))
        if self._exc is not None:
            raise self._exc
        return self._result


class _FakeOpenAI:
    def __init__(self, *, result: Any = None, exc: BaseException | None = None) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(result=result, exc=exc))


def _openai_completion(
    *, parsed: Any = None, content: str | None = None, refusal: str | None = None
) -> SimpleNamespace:
    message = SimpleNamespace(parsed=parsed, content=content, refusal=refusal)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=20,
            prompt_tokens_details=SimpleNamespace(cached_tokens=64),
        ),
        model="gpt-x",
        id="chatcmpl-1",
        _request_id="req_o",
    )


def _openai_provider(fake: _FakeOpenAI) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="openai",
        api_key_env="UNUSED",
        structured_mode="json_schema",
        token_param="max_completion_tokens",
        supports_reasoning_effort=True,
        client=fake,  # type: ignore[arg-type]
    )


def test_openai_json_schema_wires_response_format_and_reasoning_effort() -> None:
    fake = _FakeOpenAI(result=_openai_completion(parsed=_VERDICT))
    result = _openai_provider(fake).parse_structured(
        _parse_req(EdgeVerdict, model="gpt-5-mini", reasoning=True, effort="high")
    )
    method, kwargs = fake.chat.completions.calls[0]
    assert method == "parse"
    assert kwargs["response_format"] is EdgeVerdict
    assert "max_completion_tokens" in kwargs
    assert kwargs["reasoning_effort"] == "high"  # gpt-5 reasoning model
    assert result.usage == LLMUsage(input_tokens=100, output_tokens=20, cached_input_tokens=64)
    assert result.provider == "openai" and result.request_id == "req_o"


def test_openai_non_reasoning_model_omits_reasoning_effort() -> None:
    fake = _FakeOpenAI(result=_openai_completion(parsed=CandidateEdgeList(candidate_edges=[])))
    _openai_provider(fake).parse_structured(_parse_req(CandidateEdgeList, model="gpt-4o-mini"))
    _, kwargs = fake.chat.completions.calls[0]
    assert "reasoning_effort" not in kwargs


def test_openai_refusal_and_missing_parsed_raise() -> None:
    fake_refusal = _FakeOpenAI(result=_openai_completion(refusal="cannot help"))
    with pytest.raises(LLMRefusalError):
        _openai_provider(fake_refusal).parse_structured(_parse_req(EdgeVerdict))
    fake_none = _FakeOpenAI(result=_openai_completion(parsed=None))
    with pytest.raises(LLMRefusalError):
        _openai_provider(fake_none).parse_structured(_parse_req(EdgeVerdict))


def _deepseek_provider(fake: _FakeOpenAI) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="deepseek",
        api_key_env="UNUSED",
        base_url="https://api.deepseek.com",
        structured_mode="json_object",
        token_param="max_tokens",
        supports_reasoning_effort=False,
        client=fake,  # type: ignore[arg-type]
    )


def _deepseek_completion(content: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content, parsed=None, refusal=None)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=20,
            prompt_tokens_details=None,
            prompt_cache_hit_tokens=80,
        ),
        model="deepseek-chat",
        id="ds-1",
        _request_id=None,
    )


def test_deepseek_json_object_mode_validates_and_normalizes_usage() -> None:
    fake = _FakeOpenAI(result=_deepseek_completion(_VERDICT_JSON))
    result = _deepseek_provider(fake).parse_structured(
        _parse_req(EdgeVerdict, model="deepseek-chat", reasoning=True, effort="high")
    )
    method, kwargs = fake.chat.completions.calls[0]
    assert method == "create"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert "max_tokens" in kwargs  # DeepSeek uses max_tokens, not max_completion_tokens
    assert "reasoning_effort" not in kwargs  # DeepSeek does not support it
    assert "JSON schema" in kwargs["messages"][0]["content"]  # schema injected into system
    assert isinstance(result.parsed, EdgeVerdict)
    assert result.usage == LLMUsage(input_tokens=100, output_tokens=20, cached_input_tokens=80)
    assert result.request_id == "ds-1"  # falls back to completion.id when no _request_id


def test_deepseek_invalid_json_raises_refusal() -> None:
    fake = _FakeOpenAI(result=_deepseek_completion("{}"))  # missing required fields
    with pytest.raises(LLMRefusalError):
        _deepseek_provider(fake).parse_structured(_parse_req(EdgeVerdict))


def _openai_status(cls: type[openai.APIStatusError], code: int) -> openai.APIStatusError:
    resp = httpx.Response(code, request=_REQ, headers={"x-request-id": "rid"})
    return cls("boom", response=resp, body=None)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (_openai_status(openai.RateLimitError, 429), LLMRateLimitError),
        (_openai_status(openai.AuthenticationError, 401), LLMAuthError),
        (_openai_status(openai.BadRequestError, 400), LLMBadRequestError),
        (_openai_status(openai.InternalServerError, 500), LLMServiceError),
        (openai.APIConnectionError(message="x", request=_REQ), LLMConnectionError),
    ],
)
def test_openai_exception_mapping(exc: BaseException, expected: type[Exception]) -> None:
    fake = _FakeOpenAI(exc=exc)
    with pytest.raises(expected) as ei:
        _openai_provider(fake).parse_structured(_parse_req(EdgeVerdict))
    assert ei.value.provider == "openai"  # type: ignore[attr-defined]


def test_missing_api_key_raises_auth_error() -> None:
    provider = OpenAICompatibleProvider(
        name="deepseek",
        api_key_env="DEFINITELY_UNSET_KEY_VAR",
        structured_mode="json_object",
    )
    with pytest.raises(LLMAuthError):
        provider.parse_structured(_parse_req(EdgeVerdict))


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def test_registry_returns_expected_provider_types() -> None:
    assert isinstance(get_provider(LLMProvider.anthropic), AnthropicProvider)
    openai_p = get_provider(LLMProvider.openai)
    deepseek_p = get_provider(LLMProvider.deepseek)
    assert openai_p.name == "openai"
    assert deepseek_p.name == "deepseek"
