"""Live, opt-in smoke test for every LLM provider (plan/02).

Skipped unless ``VCM_LLM_SMOKE`` is set; each provider is further skipped unless its key is
present (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`). Makes real, billed
calls. Run with:

    VCM_LLM_SMOKE=1 uv run pytest tests/test_llm_smoke.py -v

Hard gate per provider: extraction returns a valid `CandidateEdgeList` and verification a
valid `EdgeVerdict`. Caching is checked via the normalized `cached_input_tokens` — strict for
Anthropic (explicit `cache_control`), best-effort for OpenAI/DeepSeek (automatic caching).
"""

from __future__ import annotations

import os

import pytest

from vcm.llm import extract_edges, verify_edge
from vcm.models import CandidateEdgeList, EdgeVerdict
from vcm.models.enums import LLMProvider

# (provider, key env var, extract model, verify model)
_PROVIDERS = [
    (LLMProvider.anthropic, "ANTHROPIC_API_KEY", "claude-sonnet-4-6", "claude-opus-4-8"),
    (LLMProvider.openai, "OPENAI_API_KEY", "gpt-4o-mini", "o4-mini"),
    (LLMProvider.deepseek, "DEEPSEEK_API_KEY", "deepseek-chat", "deepseek-chat"),
]

pytestmark = pytest.mark.skipif(
    not os.getenv("VCM_LLM_SMOKE"),
    reason="live API call; set VCM_LLM_SMOKE=1 to run",
)

_PASSAGE = (
    "On our fourth-quarter earnings call, management noted that demand for AI accelerators "
    "continued to outstrip supply. NVIDIA's data-center GPUs rely on high-bandwidth memory "
    "(HBM3E) supplied primarily by SK Hynix, with Micron and Samsung qualifying additional "
    "capacity. Advanced packaging remains the binding constraint: TSMC performs CoWoS "
    "(chip-on-wafer-on-substrate) packaging for NVIDIA's H100 and H200 GPUs, and CoWoS capacity "
    "is sold out through the year. Hyperscalers including Microsoft, Amazon, and Google are "
    "pre-paying to secure GPU allocation, and several cited supply constraints on HBM and "
    "packaging as the gating factor for their AI infrastructure build-out. We expect the profit "
    "pool to concentrate in the HBM and advanced-packaging stages, where pricing power is "
    "strongest and expansion lead times run two to three years. The migration from HBM3E toward "
    "HBM4, and from pluggable optics toward co-packaged optics, is expected to shift value among "
    "suppliers over the next several product cycles.\n\n"
)
_CHUNK = _PASSAGE * 20  # comfortably > the largest provider's min cacheable prefix

_CLAIM_A = (
    "Claim: SK Hynix SUPPLIES_TO NVIDIA (HBM3E). Asserted layer: fact. "
    "Supporting excerpt: 'high-bandwidth memory (HBM3E) supplied primarily by SK Hynix'."
)
_CLAIM_B = (
    "Claim: TSMC SUPPLIES_TO NVIDIA (CoWoS advanced packaging). Asserted layer: fact. "
    "Supporting excerpt: 'TSMC performs CoWoS ... packaging for NVIDIA's H100 and H200'."
)


def _require_key(env: str) -> None:
    if not os.getenv(env):
        pytest.skip(f"{env} not set")


@pytest.mark.parametrize(("provider", "key_env", "extract_model", "verify_model"), _PROVIDERS)
def test_provider_returns_valid_structured_output(
    provider: LLMProvider, key_env: str, extract_model: str, verify_model: str
) -> None:
    _require_key(key_env)

    extracted = extract_edges(_CHUNK, provider=provider, model=extract_model)
    assert isinstance(extracted.parsed, CandidateEdgeList)
    assert extracted.provider == provider.value

    verdict = verify_edge(_CHUNK, _CLAIM_A, provider=provider, model=verify_model)
    assert isinstance(verdict.parsed, EdgeVerdict)
    assert verdict.provider == provider.value


@pytest.mark.parametrize(("provider", "key_env", "extract_model", "verify_model"), _PROVIDERS)
def test_provider_prompt_caching(
    provider: LLMProvider, key_env: str, extract_model: str, verify_model: str
) -> None:
    _require_key(key_env)

    # Two verify calls share the same chunk prefix; only the per-edge claim varies.
    verify_edge(_CHUNK, _CLAIM_A, provider=provider, model=verify_model)
    second = verify_edge(_CHUNK, _CLAIM_B, provider=provider, model=verify_model)

    if provider is LLMProvider.anthropic:
        assert second.usage.cached_input_tokens > 0, "explicit cache_control should always read"
    elif second.usage.cached_input_tokens == 0:
        pytest.skip(f"{provider.value} automatic cache did not register on the second call")
