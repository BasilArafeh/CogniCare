"""
Extract raw text from medical PDFs: native text via PyMuPDF, OCR fallback for image pages.

Returns one RawPdfPage per page — no linguistic cleaning yet.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import fitz

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    import pytesseract
    from pytesseract.pytesseract import TesseractNotFoundError

    _HAS_OCR_DEPS = True
except ImportError:
    Image = None  # type: ignore[assignment, misc]
    pytesseract = None  # type: ignore[assignment, misc]
    TesseractNotFoundError = Exception  # type: ignore[assignment, misc]
    _HAS_OCR_DEPS = False

_tesseract_missing_logged = False

# Rough threshold: pages with fewer characters are treated as scanned / image-heavy.
EXTRACTION_MIN_CHARS = 40


@dataclass(frozen=True)
class RawPdfPage:
    """One PDF page worth of untouched extracted text plus source metadata."""

    raw_text: str
    filename: str
    page_number: int
    source_folder: str
    extraction_method: Literal["native_text", "ocr"]


def _native_page_text(page: fitz.Page) -> str:
    """Pull unicode text blocks from PDF page using PyMuPDF."""
    txt = page.get_text("text")
    return txt if txt else ""


def _needs_ocr(text: str) -> bool:
    """Decide if native extraction is empty enough that OCR fallback should run."""
    return len(text.strip()) < EXTRACTION_MIN_CHARS


def _ocr_page_text(page: fitz.Page) -> str:
    """
    Rasterize page to an image and run Tesseract OCR.

    Requires Pillow, pytesseract, and a system Tesseract install.
    """
    if not _HAS_OCR_DEPS:
        logger.warning(
            "OCR requested but Pillow/pytesseract not available — returning empty OCR text.",
        )
        return ""
    global _tesseract_missing_logged
    try:
        # 2x matrix improves small-font readability without huge memory use.
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))
        ocr_txt = pytesseract.image_to_string(image)
        return ocr_txt if ocr_txt else ""
    except TesseractNotFoundError:
        if not _tesseract_missing_logged:
            logger.warning(
                "Tesseract OCR binary not installed or not on PATH — "
                "image-heavy PDF pages may stay sparse. Install from "
                "https://github.com/tesseract-ocr/tesseract",
            )
            _tesseract_missing_logged = True
        return ""
    except Exception:
        logger.exception(
            "OCR failed on PDF page index %s (1-based=%s)",
            page.number,
            page.number + 1,
        )
        return ""


def extract_pages_from_pdf(pdf_path: Path, source_folder: str) -> list[RawPdfPage]:
    """
    Open one PDF and return raw per-page text objects with filename and folder metadata.

    Uses native text first; if a page is nearly empty, runs OCR as fallback.
    """
    path = pdf_path.resolve()
    filename = path.name
    pages_out: list[RawPdfPage] = []
    logger.info("Extracting pages from PDF: %s (folder=%s)", path, source_folder)

    try:
        doc = fitz.open(path)
    except Exception:
        logger.exception("Failed to open PDF: %s", path)
        return pages_out

    try:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            page_number = i + 1
            native = _native_page_text(page)
            native_stripped = native.strip()
            if _needs_ocr(native_stripped):
                logger.debug(
                    "Page %s in %s: low native text (%s chars) — attempting OCR.",
                    page_number,
                    filename,
                    len(native_stripped),
                )
                ocr_text = _ocr_page_text(page).strip()
                if len(ocr_text) > len(native_stripped):
                    chosen, method = ocr_text, "ocr"
                else:
                    chosen, method = native_stripped, "native_text"
                if not chosen:
                    logger.warning(
                        "Page %s in %s: both native and OCR text empty.",
                        page_number,
                        filename,
                    )
            else:
                chosen, method = native_stripped, "native_text"

            pages_out.append(
                RawPdfPage(
                    raw_text=chosen,
                    filename=filename,
                    page_number=page_number,
                    source_folder=source_folder,
                    extraction_method=method,
                )
            )
    finally:
        doc.close()

    logger.info(
        "Finished PDF %s: %s pages (native_primary=%s, ocr_fallback=%s).",
        filename,
        len(pages_out),
        sum(1 for p in pages_out if p.extraction_method == "native_text"),
        sum(1 for p in pages_out if p.extraction_method == "ocr"),
    )
    return pages_out
