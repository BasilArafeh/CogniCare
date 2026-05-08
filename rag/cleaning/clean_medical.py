"""
Turn RawPdfPage objects into cleaned plain text suitable for downstream chunking.

Order: ftfy unicode repair, then regex-based removal of page numbers, repetitive
headers/footers patterns, and simple figure/table caption lines.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import ftfy

from .pdf_pages import RawPdfPage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CleanedPdfPage:
    """Medical PDF page text after normalization and noisy line removal."""

    text: str
    filename: str
    page_number: int
    source_folder: str


def _repair_unicode(text: str) -> str:
    """Repair mojibake and odd unicode escapes using ftfy."""
    fixed = ftfy.fix_text(text)
    return fixed if fixed else text


_PAGE_NUMBER_LINE_RE = re.compile(
    r"^\s*(?:page|pg\.?)\s*\d+(?:\s*(?:/\s*|of\s*)\s*\d+)?\s*$",
    re.IGNORECASE,
)
_LINE_NUMBER_ONLY_RE = re.compile(r"^\s*-?\s*\d{1,4}\s*-?\s*$")
_FOOTER_DASH_PAGE_RE = re.compile(r"^\s*\d+\s*[-–—|]\s*\d+\s*$")
_FIG_TABLE_CAPTION_RE = re.compile(
    r"^\s*(?:figure|fig\.|table)\s+[0-9A-Za-z.-]+[^\n]{0,180}\s*$",
    re.IGNORECASE,
)


def _strip_noise_lines(lines: list[str]) -> list[str]:
    """Drop obvious page-number lines and short figure/table captions."""
    kept: list[str] = []
    for line in lines:
        s = line.rstrip()
        if not s.strip():
            kept.append("")
            continue
        if _PAGE_NUMBER_LINE_RE.match(s):
            logger.debug("Dropping page-number-style line: %r", s[:80])
            continue
        if _LINE_NUMBER_ONLY_RE.match(s):
            logger.debug("Dropping numeric-only line: %r", s[:80])
            continue
        if _FOOTER_DASH_PAGE_RE.match(s) and len(s) < 20:
            continue
        if _FIG_TABLE_CAPTION_RE.match(s):
            logger.debug("Dropping caption-style line: %r", s[:80])
            continue
        kept.append(s)
    return kept


_REPEAT_HEADER_LINE_RE = re.compile(
    r"^\s*(?:www\.|©|copyright|confidential|all rights reserved|\d{4}\s+[A-Za-z].{0,40})\s*$",
    re.IGNORECASE,
)


def _collapse_header_footer_runs(lines: list[str]) -> list[str]:
    """
    Remove very short probable header/footer boilerplate runs at chunk boundaries.

    Conservative: trims leading/trailing repetitive non-body lines (URLs, ©, years).
    """
    if not lines:
        return lines

    def is_boilerplate(line: str) -> bool:
        t = line.strip()
        return bool(t) and len(t) < 120 and bool(_REPEAT_HEADER_LINE_RE.match(t))

    # Trim leading boilerplate (first few lines).
    start = 0
    while start < min(5, len(lines)) and is_boilerplate(lines[start]):
        logger.debug("Trimming probable header line: %r", lines[start][:80])
        start += 1

    # Trim trailing boilerplate (last few lines).
    end = len(lines)
    while end > max(start, len(lines) - 5) and end > start:
        candidate = lines[end - 1]
        if candidate.strip() and is_boilerplate(candidate):
            logger.debug("Trimming probable footer line: %r", candidate[:80])
            end -= 1
            continue
        break

    return lines[start:end]


_SPACES_RE = re.compile(r"[ \t]+")
_MULTIRETURN_RE = re.compile(r"\n{3,}")


def _normalize_whitespace_blob(text: str) -> str:
    """Normalize interior spacing while keeping paragraph-ish breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _SPACES_RE.sub(" ", text)
    text = _MULTIRETURN_RE.sub("\n\n", text)
    return text.strip()


def clean_medical_pages(pages: list[RawPdfPage]) -> list[CleanedPdfPage]:
    """Run full text cleaning pipeline on extracted raw PDF pages."""
    out: list[CleanedPdfPage] = []
    for raw in pages:
        repaired = _repair_unicode(raw.raw_text or "")
        lines = repaired.splitlines()
        lines = _strip_noise_lines(lines)
        lines = _collapse_header_footer_runs(lines)
        cleaned = _normalize_whitespace_blob("\n".join(lines))
        if not cleaned:
            logger.warning(
                "Empty cleaned text for %s page %s (folder=%s).",
                raw.filename,
                raw.page_number,
                raw.source_folder,
            )
        out.append(
            CleanedPdfPage(
                text=cleaned,
                filename=raw.filename,
                page_number=raw.page_number,
                source_folder=raw.source_folder,
            )
        )
    logger.info(
        "Cleaned %s raw pages into %s cleaned pages.",
        len(pages),
        len(out),
    )
    return out
