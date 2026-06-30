"""SEC EDGAR fetch — latest 10-K for a ticker/CIK (plan/02 §Ingestion, design §11).

The URL-building and submissions-JSON parsing are pure (unit-tested with fixtures); only
``fetch_latest_10k`` does live HTTP. SEC requires a descriptive ``User-Agent``
(``config.edgar_user_agent``) and rate-limits aggressively, so this is manual/on-demand in
Phase 0 — no crawling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from vcm.config import get_settings

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"

_CONTENT_TYPE_BY_SUFFIX = {
    "htm": "text/html",
    "html": "text/html",
    "txt": "text/plain",
    "pdf": "application/pdf",
}


class IngestionError(RuntimeError):
    """Raised when a source cannot be fetched or resolved (e.g. unknown ticker)."""


@dataclass(frozen=True)
class FilingRef:
    accession_number: str
    primary_document: str
    filing_date: str  # ISO "YYYY-MM-DD"


@dataclass(frozen=True)
class FetchedDocument:
    raw: bytes
    content_type: str
    filename: str
    title: str
    url: str
    accession_number: str
    published_at: datetime | None
    cik: str


def normalize_cik(value: str) -> str | None:
    """Return a 10-digit CIK if ``value`` is a CIK (digits, optional ``CIK`` prefix), else None."""
    digits = value.strip().upper().removeprefix("CIK").lstrip(":# ").strip()
    return digits.zfill(10) if digits.isdigit() else None


def resolve_cik(ticker_or_cik: str, *, ticker_map: dict[str, Any]) -> str:
    """Resolve a ticker to a 10-digit CIK using SEC's company_tickers.json mapping."""
    cik = normalize_cik(ticker_or_cik)
    if cik is not None:
        return cik
    wanted = ticker_or_cik.strip().upper()
    for row in ticker_map.values():
        if str(row.get("ticker", "")).upper() == wanted:
            return str(row["cik_str"]).zfill(10)
    raise IngestionError(f"ticker not found in SEC company map: {ticker_or_cik!r}")


def pick_latest_filing(submissions: dict[str, Any], *, form: str = "10-K") -> FilingRef:
    """Pick the most recent filing of ``form`` from a submissions document.

    The ``filings.recent`` arrays are newest-first, so the first match is the latest.
    """
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    for i, f in enumerate(forms):
        if f == form:
            return FilingRef(
                accession_number=recent["accessionNumber"][i],
                primary_document=recent["primaryDocument"][i],
                filing_date=recent["filingDate"][i],
            )
    raise IngestionError(f"no {form} filing found in submissions")


def archive_url(cik: str, ref: FilingRef) -> str:
    cik_int = str(int(cik))  # archive paths use the un-padded CIK
    accession_nodash = ref.accession_number.replace("-", "")
    return f"{_ARCHIVES_BASE}/{cik_int}/{accession_nodash}/{ref.primary_document}"


def _content_type(primary_document: str, header: str | None) -> str:
    ct = (header or "").split(";")[0].strip().lower()
    if ct:
        return ct
    suffix = primary_document.rsplit(".", 1)[-1].lower() if "." in primary_document else ""
    return _CONTENT_TYPE_BY_SUFFIX.get(suffix, "text/html")


def _parse_filing_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": get_settings().edgar_user_agent,
            "Accept-Encoding": "gzip, deflate",
        },
        timeout=30.0,
        follow_redirects=True,
    )


def fetch_latest_10k(
    ticker_or_cik: str, *, form: str = "10-K", client: httpx.Client | None = None
) -> FetchedDocument:
    own_client = client is None
    client = client or make_client()
    try:
        cik = normalize_cik(ticker_or_cik)
        if cik is None:
            resp = client.get(_TICKERS_URL)
            resp.raise_for_status()
            cik = resolve_cik(ticker_or_cik, ticker_map=resp.json())

        subs_resp = client.get(_SUBMISSIONS_URL.format(cik=cik))
        subs_resp.raise_for_status()
        submissions = subs_resp.json()

        ref = pick_latest_filing(submissions, form=form)
        url = archive_url(cik, ref)
        doc_resp = client.get(url)
        doc_resp.raise_for_status()

        company = str(submissions.get("name", "")).strip()
        title = f"{company} {form} {ref.filing_date}".strip()
        return FetchedDocument(
            raw=doc_resp.content,
            content_type=_content_type(ref.primary_document, doc_resp.headers.get("content-type")),
            filename=ref.primary_document,
            title=title,
            url=url,
            accession_number=ref.accession_number,
            published_at=_parse_filing_date(ref.filing_date),
            cik=cik,
        )
    finally:
        if own_client:
            client.close()
