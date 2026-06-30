"""Anthropic client accessor (plan/02 §LLM layer).

Zero-arg construction resolves credentials at call time from ``ANTHROPIC_API_KEY`` or
an ``ant auth login`` profile — keys are deliberately never held in ``config`` (plan/02,
plan/README §Cross-cutting). Only model ids and the retry count come from settings.
"""

from __future__ import annotations

from functools import lru_cache

import anthropic

from vcm.config import get_settings


@lru_cache
def get_client() -> anthropic.Anthropic:
    """Return the process-wide Anthropic client (cached).

    The SDK auto-retries 429 / 5xx / connection errors with exponential backoff;
    ``llm_max_retries`` (default 2) tunes how many times.
    """
    settings = get_settings()
    return anthropic.Anthropic(max_retries=settings.llm_max_retries)
