"""Live, opt-in test: the extract -> verify pipeline on a real chunk (default provider).

Skipped unless ``VCM_LLM_SMOKE`` is set (billed LLM calls, needs ANTHROPIC_API_KEY). Proves
the two-stage pipeline end-to-end on one realistic chunk. Run with:

    VCM_LLM_SMOKE=1 uv run pytest tests/test_pipeline_live.py -v
"""

from __future__ import annotations

import os

import pytest

from vcm.pipeline import run_chunks

pytestmark = pytest.mark.skipif(
    not os.getenv("VCM_LLM_SMOKE"),
    reason="live LLM calls; set VCM_LLM_SMOKE=1 to run",
)

_CHUNK = (
    "NVIDIA's data-center GPUs rely on high-bandwidth memory (HBM3E) supplied primarily by "
    "SK Hynix, with Micron qualifying additional capacity. TSMC performs CoWoS advanced "
    "packaging for NVIDIA's H100 and H200 GPUs, and CoWoS capacity is sold out through the "
    "year. Hyperscalers including Microsoft and Amazon are pre-paying to secure GPU allocation."
)


def test_pipeline_extracts_and_verifies_real_chunk() -> None:
    result = run_chunks([_CHUNK])
    assert result.chunks_processed == 1
    assert result.extracted >= 1, "expected at least one candidate edge from the chunk"
    assert len(result.verified) <= result.extracted
    assert result.usage.input_tokens > 0
    # every verified edge carries its supporting excerpt and a verdict reason
    for edge in result.verified:
        assert edge.candidate.excerpt or edge.candidate.layer.value != "fact"
        assert edge.verdict.reason
