"""Provider registry — maps the configured `LLMProvider` to an implementation (plan/02).

Cached so each provider (and its underlying SDK client) is built once. The implementations
resolve their API key from env lazily, so importing this never needs credentials.
"""

from __future__ import annotations

from functools import lru_cache

from vcm.config import get_settings
from vcm.llm.base import StructuredLLM
from vcm.llm.providers.anthropic import AnthropicProvider
from vcm.llm.providers.openai_compat import OpenAICompatibleProvider
from vcm.models.enums import LLMProvider


@lru_cache
def get_provider(provider: LLMProvider) -> StructuredLLM:
    if provider is LLMProvider.anthropic:
        return AnthropicProvider()
    if provider is LLMProvider.openai:
        return OpenAICompatibleProvider(
            name="openai",
            api_key_env="OPENAI_API_KEY",
            structured_mode="json_schema",
            token_param="max_completion_tokens",
            supports_reasoning_effort=True,
        )
    if provider is LLMProvider.deepseek:
        return OpenAICompatibleProvider(
            name="deepseek",
            api_key_env="DEEPSEEK_API_KEY",
            base_url=get_settings().deepseek_base_url,
            structured_mode="json_object",
            token_param="max_tokens",
            supports_reasoning_effort=False,
        )
    raise ValueError(f"unknown provider: {provider!r}")
