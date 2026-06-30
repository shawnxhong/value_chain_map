"""Document parsing: raw bytes -> markdown/text -> chunks (plan/02-pipeline-and-llm.md)."""

from vcm.parsing.chunk import TextChunk, chunk_text
from vcm.parsing.parse import ParsingError, html_to_text, parse_document

__all__ = [
    "TextChunk",
    "chunk_text",
    "ParsingError",
    "html_to_text",
    "parse_document",
]
