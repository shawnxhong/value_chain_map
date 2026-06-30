"""Text -> chunks (plan/02 §Parsing).

Splits on paragraph (blank-line) boundaries and greedily packs paragraphs up to a target
character budget, keeping byte-accurate offsets back into the source text so an excerpt can
later be located within its chunk. A single oversized paragraph is hard-split. ``token_count``
is a cheap ~4-chars/token estimate (chunk metadata only — not used for billing/limits).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vcm.config import get_settings

_PARAGRAPH_SEP = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class TextChunk:
    ordinal: int
    text: str
    char_start: int
    char_end: int
    token_count: int


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of non-empty paragraphs, in order."""
    spans: list[tuple[int, int]] = []
    pos = 0
    for sep in _PARAGRAPH_SEP.finditer(text):
        if text[pos : sep.start()].strip():
            spans.append((pos, sep.start()))
        pos = sep.end()
    if text[pos:].strip():
        spans.append((pos, len(text)))
    return spans


def chunk_text(text: str, *, target_chars: int | None = None) -> list[TextChunk]:
    target = target_chars if target_chars is not None else get_settings().chunk_target_chars
    spans = _paragraph_spans(text)

    regions: list[tuple[int, int]] = []  # (start, end) of each chunk in the source text
    cur: tuple[int, int] | None = None
    for start, end in spans:
        if end - start > target:  # oversized paragraph: flush, then hard-split it
            if cur is not None:
                regions.append(cur)
                cur = None
            pos = start
            while pos < end:
                stop = min(pos + target, end)
                regions.append((pos, stop))
                pos = stop
            continue
        if cur is None:
            cur = (start, end)
        elif end - cur[0] <= target:
            cur = (cur[0], end)  # extend current chunk to include this paragraph
        else:
            regions.append(cur)
            cur = (start, end)
    if cur is not None:
        regions.append(cur)

    return [
        TextChunk(
            ordinal=i,
            text=text[a:b],
            char_start=a,
            char_end=b,
            token_count=_estimate_tokens(text[a:b]),
        )
        for i, (a, b) in enumerate(regions)
    ]
