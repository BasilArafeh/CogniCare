"""
Detect section headings in cleaned PDF text lines (patterns only — no splitting).

Recognizes numbered headings such as ``3.1 Symptoms`` and ALL-CAPS prose titles.
"""

from __future__ import annotations

import re

# Hierarchical numbering: ``3.12 Title`` … (dot chain before title).
_DECIMAL_HEADING_RE = re.compile(r"^\s*\d+(?:\.\d+)+[\.)]?\s+(.{3,})$")
# Single digit ``1 Title`` vs ``12 mg`` — digit then dot/paren terminator.
_DOT_ENUM_HEADING_RE = re.compile(r"^\s*\d+[\.)]\s+(.{3,})$")
# Space-only enum like ``6 ADVERSE REACTIONS …`` requires uppercase title cue.
_SPACE_ENUM_HEADING_RE = re.compile(r"^\s*\d{1,2}\s+([A-Z][^\n]{2,})$")

# Mostly ALL CAPS line (mixed digits/punctuation OK); rejects very short/long garble.
_LINE_ALL_CAPS_BODY_RE = re.compile(r"^[A-Z0-9][A-Z0-9\s,\.;:'\"!?&()/_-]+$")


def detect_section_boundary_line(line: str) -> str | None:
    """
    Return a normalized heading title when a single line opens a section, else None.

    Implements numbered headings first, then ALL-CAPS heuristic lines typical of NIH/PDF brochures.
    """
    raw = line.strip()
    if not raw:
        return None

    decimal = _DECIMAL_HEADING_RE.match(raw)
    if decimal:
        return decimal.group(1).strip()[:240]

    dotted = _DOT_ENUM_HEADING_RE.match(raw)
    if dotted:
        return dotted.group(1).strip()[:240]

    spaced = _SPACE_ENUM_HEADING_RE.match(raw)
    if spaced and not spaced.group(1).lower().startswith(
        ("mg ", "mcg ", "ml ", "ml/", "µg ", "µg/")
    ):
        return spaced.group(1).strip()[:240]

    if _looks_like_all_caps_heading(raw):
        return raw[:240]
    return None


def detect_section_title_for_text_block(prefix_text: str) -> str | None:
    """
    Scan the beginning of a text block's lines and return first detected section title.

    Used when chunk_medical needs a coarse heading before character splitting.
    """
    for ln in prefix_text.strip().splitlines()[:12]:
        t = detect_section_boundary_line(ln)
        if t:
            return t
    return None


def _looks_like_all_caps_heading(s: str) -> bool:
    """Heuristic: stand-alone shouting title vs normal sentence casing."""
    if len(s) < 6 or len(s) > 200:
        return False
    if not _LINE_ALL_CAPS_BODY_RE.match(s):
        return False
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 6:
        return False
    # Require strong uppercase dominance (handles odd symbols).
    uppers = sum(1 for c in letters if c.isupper())
    return uppers / len(letters) >= 0.85
