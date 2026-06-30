"""Raw bytes -> plain text / markdown (plan/02 §Parsing).

Phase 0 handles the formats the spine actually needs with zero heavy deps: plain text and
markdown decode directly; HTML (SEC 10-K primary documents) is flattened with a stdlib
``HTMLParser``. PDF/deck parsing is routed to Docling from the ``[parse]`` extra and
lazy-imported, so the core install and tests never pull the heavy stack; without it, PDF
ingestion raises a clear, actionable error.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_HTML_SKIP = {"script", "style", "head", "title", "meta", "link", "noscript"}
_HTML_BLOCK = {
    "p",
    "div",
    "br",
    "li",
    "ul",
    "ol",
    "tr",
    "table",
    "thead",
    "tbody",
    "section",
    "article",
    "header",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
}
_WS_RUN = re.compile(r"[ \t]+")
_BLANK_RUN = re.compile(r"\n{3,}")


class ParsingError(RuntimeError):
    """Raised when a document cannot be parsed (unsupported format / missing extra)."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in _HTML_SKIP:
            self._skip_depth += 1
        elif tag in _HTML_BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _HTML_SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in _HTML_BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def html_to_text(html: str) -> str:
    """Flatten HTML to readable text: drop script/style, turn block tags into newlines."""
    extractor = _TextExtractor()
    extractor.feed(html)
    extractor.close()
    lines = [_WS_RUN.sub(" ", line).strip() for line in extractor.text().splitlines()]
    # drop leading blanks and collapse consecutive blank lines
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1] != ""):
            out.append(line)
    return _BLANK_RUN.sub("\n\n", "\n".join(out)).strip()


def _kind(content_type: str | None, filename: str | None) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in {"text/html", "application/xhtml+xml"}:
        return "html"
    if ct == "application/pdf":
        return "pdf"
    if ct in {"text/markdown", "text/x-markdown"}:
        return "markdown"
    if ct.startswith("text/"):
        return "text"
    suffix = ""
    if filename and "." in filename:
        suffix = filename.rsplit(".", 1)[-1].lower()
    return {
        "html": "html",
        "htm": "html",
        "xhtml": "html",
        "pdf": "pdf",
        "md": "markdown",
        "markdown": "markdown",
        "txt": "text",
        "text": "text",
    }.get(suffix, "text")  # default: treat as decodable text


def parse_document(
    raw: bytes, *, content_type: str | None = None, filename: str | None = None
) -> str:
    """Decode/flatten ``raw`` to plain text/markdown based on content type or filename."""
    kind = _kind(content_type, filename)
    if kind == "pdf":
        return _parse_pdf(raw)
    text = raw.decode("utf-8", errors="replace")
    if kind == "html":
        return html_to_text(text)
    return text  # text / markdown pass through


def _parse_pdf(raw: bytes) -> str:
    """Parse a PDF via Docling (the ``[parse]`` extra). Untested in Phase 0 (Docling not
    installed locally); wired so installing the extra enables it."""
    try:
        from docling.datamodel.base_models import DocumentStream  # type: ignore[import-not-found]
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]
    except ImportError as e:
        raise ParsingError(
            "PDF parsing requires the optional parsing stack. Install it with "
            "`uv pip install -e '.[parse]'` (Docling), or upload text/HTML instead."
        ) from e

    import io

    stream = DocumentStream(name="document.pdf", stream=io.BytesIO(raw))
    result = DocumentConverter().convert(stream)
    return result.document.export_to_markdown()
