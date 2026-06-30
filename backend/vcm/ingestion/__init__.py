"""Source manager: manual upload + SEC EDGAR (10-K) fetch (plan/02-pipeline-and-llm.md)."""

from vcm.ingestion.edgar import (
    FetchedDocument,
    IngestionError,
    fetch_latest_10k,
)
from vcm.ingestion.service import (
    IngestResult,
    ingest_document,
    ingest_edgar_10k,
    ingest_upload,
)
from vcm.ingestion.store import ObjectStore, StoredObject

__all__ = [
    "FetchedDocument",
    "IngestionError",
    "fetch_latest_10k",
    "IngestResult",
    "ingest_document",
    "ingest_edgar_10k",
    "ingest_upload",
    "ObjectStore",
    "StoredObject",
]
