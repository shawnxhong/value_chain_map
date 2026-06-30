"""Offline tests for parsing: HTML flattening, chunking, format dispatch."""

from __future__ import annotations

import pytest

from vcm.parsing import ParsingError, chunk_text, html_to_text, parse_document
from vcm.parsing.chunk import _paragraph_spans

# --------------------------------------------------------------------------- #
# html_to_text
# --------------------------------------------------------------------------- #


def test_html_to_text_drops_script_style_and_blocks_to_newlines() -> None:
    html = (
        "<html><head><title>T</title><style>.x{}</style></head>"
        "<body><p>First paragraph.</p><script>ignore()</script>"
        "<div>Second block</div></body></html>"
    )
    text = html_to_text(html)
    assert "ignore()" not in text and ".x{}" not in text and "T" not in text.splitlines()[0:1]
    assert "First paragraph." in text
    assert "Second block" in text
    # block tags produce line breaks between the two pieces
    assert "First paragraph." in text and "\n" in text


def test_html_to_text_collapses_whitespace() -> None:
    text = html_to_text("<p>a   b\t\tc</p>")
    assert "a b c" in text


# --------------------------------------------------------------------------- #
# chunk_text
# --------------------------------------------------------------------------- #


def test_chunk_offsets_reconstruct_source() -> None:
    text = "Alpha paragraph.\n\nBeta paragraph.\n\nGamma paragraph."
    chunks = chunk_text(text, target_chars=20)
    for c in chunks:
        assert text[c.char_start : c.char_end] == c.text
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert len(chunks) >= 2  # 20-char budget splits three ~16-char paragraphs


def test_chunk_packs_paragraphs_up_to_target() -> None:
    text = "\n\n".join(["x" * 10] * 6)  # six 10-char paragraphs
    chunks = chunk_text(text, target_chars=35)
    # each chunk holds several paragraphs but stays within ~target
    assert all(c.char_end - c.char_start <= 35 for c in chunks)
    assert len(chunks) >= 2


def test_chunk_hard_splits_oversized_paragraph() -> None:
    text = "y" * 250  # single paragraph, no blank lines
    chunks = chunk_text(text, target_chars=100)
    assert [len(c.text) for c in chunks] == [100, 100, 50]
    assert "".join(c.text for c in chunks) == text


def test_chunk_empty_and_whitespace() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  \t ") == []


def test_paragraph_spans_skip_blank_paragraphs() -> None:
    text = "one\n\n\n\ntwo"
    assert _paragraph_spans(text) == [(0, 3), (text.index("two"), len(text))]


# --------------------------------------------------------------------------- #
# parse_document dispatch
# --------------------------------------------------------------------------- #


def test_parse_document_text_and_markdown_passthrough() -> None:
    assert parse_document(b"plain text", content_type="text/plain") == "plain text"
    assert parse_document(b"# title", filename="notes.md") == "# title"


def test_parse_document_html_is_flattened() -> None:
    out = parse_document(b"<p>Hello</p><p>World</p>", content_type="text/html")
    assert "Hello" in out and "World" in out and "<p>" not in out


def test_parse_document_pdf_without_extra_raises() -> None:
    with pytest.raises(ParsingError, match=r"\[parse\]"):
        parse_document(b"%PDF-1.7 ...", content_type="application/pdf")
