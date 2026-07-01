"""Offline checks for the seed module (the live run needs a DB + LLM, exercised via docker)."""

from __future__ import annotations

from vcm.seed import SEED_TRANSCRIPT, StepSummary, run_seed


def test_seed_transcript_names_the_expected_entities() -> None:
    # the embedded transcript must name the relationships the extractor should find
    for token in ["SK Hynix", "TSMC", "CoWoS", "HBM3E", "H100", "hyperscaler"]:
        assert token in SEED_TRANSCRIPT


def test_step_summary_fields() -> None:
    fields = StepSummary.__dataclass_fields__
    assert {"extracted", "verified", "edges_written", "nodes_created", "rejected"} <= set(fields)


def test_run_seed_is_callable() -> None:
    # signature guard (the body needs a DB + network, so it is not invoked here)
    assert callable(run_seed)
