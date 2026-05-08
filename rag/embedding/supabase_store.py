from __future__ import annotations

import logging

from rag.chunking.schemas import MedicalChunk, MedicationChunk
from rag.db.db import get_connection

logger = logging.getLogger(__name__)

_INSERT_MEDICAL = """
INSERT INTO medical_documents (
    content,
    embedding,
    source_folder,
    filename,
    page_number,
    section_title,
    chunk_index
) VALUES ($1, $2, $3, $4, $5, $6, $7)
"""

_INSERT_MEDICATION = """
INSERT INTO medication_documents (
    content,
    embedding,
    generic_name,
    brand_names,
    drug_class,
    manufacturer,
    chunk_type,
    chunk_index
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
"""


async def store_medical_chunks(
    pairs: list[tuple[MedicalChunk, list[float]]],
) -> None:
    if not pairs:
        logger.info("store_medical_chunks: inserted 0 rows")
        return

    records = [
        (
            chunk.text,
            vector,
            chunk.source_folder,
            chunk.filename,
            chunk.page_number,
            chunk.section_title,
            chunk.chunk_index,
        )
        for chunk, vector in pairs
    ]

    async with get_connection() as conn:
        await conn.executemany(_INSERT_MEDICAL, records)

    logger.info("store_medical_chunks: inserted %s rows", len(pairs))


async def store_medication_chunks(
    pairs: list[tuple[MedicationChunk, list[float]]],
) -> None:
    if not pairs:
        logger.info("store_medication_chunks: inserted 0 rows")
        return

    records = [
        (
            chunk.text,
            vector,
            chunk.generic_name,
            chunk.brand_names,
            chunk.drug_class,
            chunk.manufacturer,
            chunk.chunk_type,
            chunk.chunk_index,
        )
        for chunk, vector in pairs
    ]

    async with get_connection() as conn:
        await conn.executemany(_INSERT_MEDICATION, records)

    logger.info("store_medication_chunks: inserted %s rows", len(pairs))
