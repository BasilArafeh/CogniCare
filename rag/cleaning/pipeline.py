"""
High-level cleaning entrypoints: walk default data dirs, extract PDFs, load medicines JSON.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rag.config import DOCUMENTS_ROOT, MEDICINES_ROOT

from .clean_medical import CleanedPdfPage, clean_medical_pages
from .clean_medications import load_and_clean_all_medication_files
from .pdf_pages import extract_pages_from_pdf

logger = logging.getLogger(__name__)


def _process_medical_documents_tree(root: Path) -> list[CleanedPdfPage]:
    """Walk immediate subdirectories of documents_root for PDF ingestion."""
    out: list[CleanedPdfPage] = []
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        if sub.name.startswith("."):
            logger.debug("Skipping hidden directory %s.", sub.name)
            continue
        folder_name = sub.name
        for pdf_path in sorted(sub.glob("*.pdf")):
            try:
                raw_pages = extract_pages_from_pdf(pdf_path, folder_name)
                out.extend(clean_medical_pages(raw_pages))
            except Exception:
                logger.exception(
                    "Failed processing PDF %s in folder %s.",
                    pdf_path.name,
                    folder_name,
                )
    return out


def clean_medical_pdfs(documents_root: Path | None = None) -> list[CleanedPdfPage]:
    """
    Discover PDFs under the medical documents tree, extract each page, and clean text.

    Expects immediate subfolders (e.g. alzheimers_and_other_sicknesses) each containing *.pdf files.
    Default root: DOCUMENTS_ROOT from rag.config (override if your corpus lives elsewhere).
    """
    root = documents_root or DOCUMENTS_ROOT
    root = root.resolve()
    if not root.is_dir():
        logger.warning(
            "Documents root missing or not a directory: %s — returning empty list.",
            root,
        )
        return []

    cleaned: list[CleanedPdfPage] = []
    cleaned.extend(_process_medical_documents_tree(root))

    logger.info(
        "clean_medical_pdfs complete under %s: %s cleaned pages.",
        root,
        len(cleaned),
    )
    return cleaned


def clean_medications(medicines_dir: Path | None = None) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """
    Load and validate medicines/*.json, returning (metadata dict, prose dict) per drug.

    Default directory: MEDICINES_ROOT from rag.config.
    """
    base = medicines_dir or MEDICINES_ROOT
    return load_and_clean_all_medication_files(base)
