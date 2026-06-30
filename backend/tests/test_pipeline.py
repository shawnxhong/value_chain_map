"""Offline tests for the extract -> verify pipeline (fakes, no network)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from vcm.llm import LLMRefusalError, LLMResult, LLMUsage
from vcm.models import CandidateEdge, CandidateEdgeList, EconomicDirection, EdgeVerdict
from vcm.models.enums import ConfidenceLabel, Layer, PaymentType, RelationshipType
from vcm.pipeline import run_chunks
from vcm.verification import format_claim

_SUPPLIES = CandidateEdge(
    source="SK Hynix",
    target="NVIDIA",
    relationship_type=RelationshipType.SUPPLIES_TO,
    layer=Layer.fact,
    excerpt="HBM3E supplied primarily by SK Hynix",
    confidence_label=ConfidenceLabel.high,
    confidence_reason="directly stated",
    economic_direction=EconomicDirection(
        payer="NVIDIA", receiver="SK Hynix", payment_type=PaymentType.component_cost
    ),
)
_COMPETES = CandidateEdge(
    source="AMD",
    target="NVIDIA",
    relationship_type=RelationshipType.COMPETES_WITH,
    layer=Layer.inference,
    excerpt="",
    confidence_label=ConfidenceLabel.low,
    confidence_reason="implied",
)


class _FakeLLM:
    """A StructuredLLM that returns canned extraction / verification output."""

    name = "fake"

    def __init__(
        self,
        *,
        candidates: list[CandidateEdge] | None = None,
        verdict: Callable[[str], EdgeVerdict | None] | None = None,
        refuse_extract: bool = False,
    ) -> None:
        self._candidates = candidates or []
        self._verdict = verdict
        self._refuse_extract = refuse_extract

    def parse_structured(self, req: Any) -> LLMResult[Any]:
        if req.output_format is CandidateEdgeList:
            if self._refuse_extract:
                raise LLMRefusalError("refused", provider=self.name)
            parsed: Any = CandidateEdgeList(candidate_edges=self._candidates)
        else:
            assert self._verdict is not None
            v = self._verdict(req.question)
            if v is None:
                raise LLMRefusalError("refused", provider=self.name)
            parsed = v
        return LLMResult(
            parsed=parsed,
            usage=LLMUsage(10, 5, 2),
            provider=self.name,
            model=req.model,
            request_id="r",
            finish_reason="stop",
        )


def _verdict(claim: str) -> EdgeVerdict:
    if "SK Hynix" in claim:  # supported, but downgrade fact -> estimate
        return EdgeVerdict(
            supported=True,
            correct_layer=Layer.estimate,
            correct_confidence_label=ConfidenceLabel.medium,
            reason="supported but inferred",
        )
    return EdgeVerdict(
        supported=False,
        correct_layer=Layer.inference,
        correct_confidence_label=ConfidenceLabel.low,
        reason="not in chunk",
    )


def test_run_chunks_keeps_supported_and_applies_corrections() -> None:
    result = run_chunks(
        ["chunk text"],
        extract_provider=_FakeLLM(candidates=[_SUPPLIES, _COMPETES]),
        verify_provider=_FakeLLM(verdict=_verdict),
    )
    assert result.chunks_processed == 1
    assert result.extracted == 2
    assert result.unsupported == 1
    assert len(result.verified) == 1

    edge = result.verified[0]
    assert edge.candidate.source == "SK Hynix"
    assert edge.candidate.layer is Layer.estimate  # corrected from fact
    assert edge.candidate.confidence_label is ConfidenceLabel.medium
    assert edge.chunk_ordinal == 0
    # usage = 1 extract + 2 verify calls, each LLMUsage(10, 5, 2)
    assert result.usage == LLMUsage(input_tokens=30, output_tokens=15, cached_input_tokens=6)


def test_run_chunks_verify_refusal_counts_unsupported() -> None:
    result = run_chunks(
        ["chunk text"],
        extract_provider=_FakeLLM(candidates=[_COMPETES]),
        verify_provider=_FakeLLM(verdict=lambda _claim: None),  # always refuses
    )
    assert result.extracted == 1
    assert result.unsupported == 1
    assert result.verified == []


def test_run_chunks_extract_refusal_skips_chunk() -> None:
    result = run_chunks(
        ["chunk text"],
        extract_provider=_FakeLLM(refuse_extract=True),
        verify_provider=_FakeLLM(verdict=_verdict),
    )
    assert result.chunks_processed == 1
    assert result.extracted == 0
    assert result.verified == []


def test_run_chunks_multiple_chunks_track_ordinal() -> None:
    result = run_chunks(
        ["chunk a", "chunk b"],
        extract_provider=_FakeLLM(candidates=[_SUPPLIES]),
        verify_provider=_FakeLLM(verdict=_verdict),
    )
    assert result.chunks_processed == 2
    assert {e.chunk_ordinal for e in result.verified} == {0, 1}


def test_format_claim_includes_edge_and_excerpt() -> None:
    claim = format_claim(_SUPPLIES)
    assert "SK Hynix" in claim
    assert "NVIDIA" in claim
    assert "SUPPLIES_TO" in claim
    assert "HBM3E supplied primarily by SK Hynix" in claim
    assert "pays" in claim  # economic direction rendered
