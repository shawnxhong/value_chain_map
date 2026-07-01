"""Phase 0 seed + end-to-end run (plan/05 Task 9 — the Phase 0 DoD).

Ingests one transcript (an embedded HBM -> packaging -> GPU -> server -> hyperscaler call) and,
by default, one real SEC 10-K, runs the extract -> verify pipeline over their chunks, and persists
the verified candidate edges (``status=candidate``) for the given chain. Prints a summary and the
candidate queue so a reviewer can then confirm edges (review API / the graph UI).

    python -m vcm.seed                       # transcript + NVDA 10-K (8 chunks), chain=hbm
    python -m vcm.seed --no-edgar            # transcript only (no network / no EDGAR)
    python -m vcm.seed --ticker AMD --max-chunks 4
    python -m vcm.seed --dry-run             # run the pipeline but do not write edges

This calls the extraction/verification models (billed). ``--max-chunks`` bounds the 10-K pass.
"""

from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass

from vcm.db.models import Document
from vcm.db.session import session_scope
from vcm.graph import persist_verified_edges
from vcm.ingestion.edgar import IngestionError
from vcm.ingestion.service import ingest_edgar_10k, ingest_upload
from vcm.models.enums import SourceType
from vcm.pipeline import run_document
from vcm.review import list_candidates

# A representative earnings-call transcript for the HBM/GPU sub-chain. Real transcripts are
# paywalled (design §11 P0), so this stands in to prove the spine; it names the relationships the
# extractor should find (SUPPLIES_TO / PRODUCES / SERVES_MARKET / BELONGS_TO_STAGE).
SEED_TRANSCRIPT = """\
Operator: Welcome to the fiscal Q4 earnings call. Here is management's prepared commentary.

CEO: Demand for our data-center GPUs remained well ahead of supply this quarter. Our H100 and
newer H200 accelerators are built on TSMC's CoWoS advanced packaging, and CoWoS capacity continues
to be the binding constraint on how many units we can ship. We are working with TSMC to expand that
packaging capacity through next year.

CEO: Each accelerator integrates high-bandwidth memory. SK Hynix is our primary supplier of HBM3E,
with Micron and Samsung qualifying additional capacity. HBM availability, alongside CoWoS, gates our
output. We pre-pay and hold long-term agreements with these suppliers to secure allocation.

CFO: Our GPUs are integrated into AI servers by our system partners, and the large hyperscalers --
the major cloud providers -- are the ultimate buyers of that capacity. One hyperscale customer
accounted for a meaningful double-digit share of revenue this year, though we do not disclose the
name. Gross margins expanded as pricing held firm given the supply-demand imbalance.

CEO: We see the profit pool concentrating in the scarce links -- advanced packaging and HBM --
where capacity cannot be added quickly. Competition among accelerator vendors is intensifying, but
the packaging and memory bottlenecks remain the story for the coming year.
"""


@dataclass
class StepSummary:
    label: str
    document_id: uuid.UUID
    chunks: int
    extracted: int
    verified: int
    unsupported: int
    nodes_created: int
    edges_written: int
    rejected: int


def _ingest_transcript() -> uuid.UUID:
    with session_scope() as session:
        result = ingest_upload(
            session,
            data=SEED_TRANSCRIPT.encode("utf-8"),
            filename="hbm_seed_transcript.txt",
            source_type=SourceType.transcript,
            title="HBM/GPU supply-chain earnings call (seed)",
            content_type="text/plain",
        )
        return result.document.id


def _ingest_edgar(ticker: str) -> uuid.UUID:
    with session_scope() as session:
        result = ingest_edgar_10k(session, ticker_or_cik=ticker)
        return result.document.id


def _run_and_persist(
    label: str, document_id: uuid.UUID, *, chain: str, max_chunks: int | None, persist: bool
) -> StepSummary:
    with session_scope() as session:
        result = run_document(session, document_id, max_chunks=max_chunks)
        nodes_created = edges_written = rejected = 0
        if persist:
            document = session.get(Document, document_id)
            assert document is not None
            pr = persist_verified_edges(session, document, result.verified, chain=chain)
            nodes_created = pr.nodes_created
            edges_written = sum(1 for e in pr.edge_ids if e is not None)
            rejected = pr.rejected
        return StepSummary(
            label=label,
            document_id=document_id,
            chunks=result.chunks_processed,
            extracted=result.extracted,
            verified=len(result.verified),
            unsupported=result.unsupported,
            nodes_created=nodes_created,
            edges_written=edges_written,
            rejected=rejected,
        )


def _print_summary(steps: list[StepSummary], chain: str, persist: bool) -> None:
    print("\n=== Seed run summary ===")
    for s in steps:
        print(
            f"[{s.label}] doc={s.document_id} chunks={s.chunks} "
            f"extracted={s.extracted} verified={s.verified} unsupported={s.unsupported} "
            f"nodes+={s.nodes_created} edges_written={s.edges_written} rejected={s.rejected}"
        )
    if not persist:
        print("(--dry-run: no edges written)")
        return
    with session_scope() as session:
        candidates = list_candidates(session, chain=chain, limit=50)
    print(f"\nCandidate edges awaiting review for chain '{chain}': {len(candidates)}")
    for view in candidates[:15]:
        e = view.edge
        print(
            f"  - {view.source_name} --{e.relationship_type.value}--> {view.target_name} "
            f"[{e.layer.value}/{e.confidence_label.value}]"
        )
    print("\nConfirm edges via the graph UI or: POST /api/review/edge/{edge_id}/confirm")


def run_seed(
    *, ticker: str, chain: str, max_chunks: int | None, edgar: bool, persist: bool
) -> list[StepSummary]:
    steps: list[StepSummary] = []

    transcript_doc = _ingest_transcript()
    steps.append(
        _run_and_persist(
            "transcript", transcript_doc, chain=chain, max_chunks=None, persist=persist
        )
    )

    if edgar:
        try:
            edgar_doc = _ingest_edgar(ticker)
        except IngestionError as e:
            print(f"EDGAR ingest failed for {ticker}: {e} (skipping the 10-K pass)")
        else:
            steps.append(
                _run_and_persist(
                    f"10-K:{ticker}",
                    edgar_doc,
                    chain=chain,
                    max_chunks=max_chunks,
                    persist=persist,
                )
            )
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 0 seed + end-to-end pipeline run.")
    parser.add_argument("--ticker", default="NVDA", help="ticker/CIK for the EDGAR 10-K pass")
    parser.add_argument("--chain", default="hbm", help="chain tag for persisted nodes/edges")
    parser.add_argument(
        "--max-chunks", type=int, default=8, help="bound the 10-K pass (cost); 0 = all chunks"
    )
    parser.add_argument("--no-edgar", action="store_true", help="skip the live EDGAR 10-K pass")
    parser.add_argument("--dry-run", action="store_true", help="run the pipeline but write nothing")
    args = parser.parse_args()

    max_chunks = None if args.max_chunks == 0 else args.max_chunks
    steps = run_seed(
        ticker=args.ticker,
        chain=args.chain,
        max_chunks=max_chunks,
        edgar=not args.no_edgar,
        persist=not args.dry_run,
    )
    _print_summary(steps, args.chain, persist=not args.dry_run)


if __name__ == "__main__":
    main()
