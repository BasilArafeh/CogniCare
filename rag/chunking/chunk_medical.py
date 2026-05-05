"""
Produce MedicalChunk objects from cleaned PDF pages using section cues + recursive splitting.

Section headings are inferred line-by-line (section_detect) before RecursiveCharacter splitting
(paragraph / line / whitespace priority), measured with tiktoken per rag.config chunk sizes.
"""

from __future__ import annotations

import logging

from rag.cleaning import CleanedPdfPage

from .schemas import MedicalChunk
from .section_detect import detect_section_boundary_line
from .text_splitter_factory import create_medical_text_splitter

logger = logging.getLogger(__name__)


def _partition_text_by_heading_lines(full_text: str) -> list[tuple[str, str]]:
    """Split body into (section_title, body_text) spans when heading lines occur."""
    lines = full_text.splitlines()
    spans: list[tuple[str, str]] = []
    current_title = ""
    buffer: list[str] = []

    for line in lines:
        boundary = detect_section_boundary_line(line)
        if boundary is not None:
            merged = "\n".join(buffer).strip()
            if merged:
                spans.append((current_title, merged))
            buffer = []
            current_title = boundary
            continue
        buffer.append(line)

    tail = "\n".join(buffer).strip()
    if tail:
        spans.append((current_title, tail))
    elif not spans and full_text.strip():
        spans.append(("", full_text.strip()))

    return spans


def chunk_medical(pages: list[CleanedPdfPage]) -> list[MedicalChunk]:
    """Flatten cleaned PDF pages into embedd-ready MedicalChunk records."""
    splitter = create_medical_text_splitter()
    chunks: list[MedicalChunk] = []

    for page in pages:
        if not page.text.strip():
            logger.warning(
                "Skipping empty page %s in %s (%s)",
                page.page_number,
                page.filename,
                page.source_folder,
            )
            continue

        spans = _partition_text_by_heading_lines(page.text)
        if not spans:
            logger.warning(
                "No text spans parsed for page %s in %s",
                page.page_number,
                page.filename,
            )
            continue

        local_index = 0
        for section_title, body in spans:
            pieces = splitter.split_text(body.strip()) if body.strip() else []
            for piece in pieces:
                trimmed = piece.strip()
                if not trimmed:
                    continue
                chunks.append(
                    MedicalChunk(
                        text=trimmed,
                        source_folder=page.source_folder,
                        filename=page.filename,
                        page_number=page.page_number,
                        section_title=section_title,
                        chunk_index=local_index,
                    )
                )
                local_index += 1

    logger.info("chunk_medical produced %s chunks from %s pages.", len(chunks), len(pages))
    return chunks
