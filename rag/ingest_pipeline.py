"""
End-to-end RAG ingestion: clean → chunk → embed → store for medical PDFs and medication JSON.
"""

from __future__ import annotations

import asyncio
import logging

from rag.chunking import chunk_medical, chunk_medications
from rag.cleaning import clean_medical_pdfs, clean_medications
from rag.config import DOCUMENTS_ROOT, MEDICINES_ROOT
from rag.db import close_pool, verify_database_connection
from rag.embedding import (
    embed_chunks,
    store_medical_chunks,
    store_medication_chunks,
)

logger = logging.getLogger(__name__)


async def run_ingestion() -> None:
    """Medical branch, then medication branch; DB pool cleanup always runs."""

    try:
        logger.info("Medical: cleaning PDFs under %s", DOCUMENTS_ROOT)
        cleaned_pages = clean_medical_pdfs()
        logger.info("Medical: cleaned %s page(s)", len(cleaned_pages))

        logger.info("Medical: chunking")
        medical_chunks = chunk_medical(cleaned_pages)
        logger.info("Medical: %s chunk(s)", len(medical_chunks))

        logger.info("Medication: loading JSON under %s", MEDICINES_ROOT)
        meds = clean_medications()
        logger.info("Medication: %s drug record(s)", len(meds))

        logger.info("Medication: chunking")
        med_chunks = chunk_medications(meds)
        logger.info("Medication: %s chunk(s)", len(med_chunks))

        needs_embeddings = bool(medical_chunks) or bool(med_chunks)
        if needs_embeddings:
            logger.info(
                "Postgres: verifying DATABASE_URL pool and connection "
                "(before OpenAI embeddings)"
            )
            await verify_database_connection()
            logger.info("Postgres: connection OK")

        if medical_chunks:
            logger.info("Medical: embedding via OpenAI (batched)")
            medical_pairs = await asyncio.to_thread(embed_chunks, medical_chunks)
            logger.info("Medical: embedded %s vector(s)", len(medical_pairs))

            logger.info("Medical: writing to Postgres")
            await store_medical_chunks(medical_pairs)
            logger.info("Medical: store complete")
        else:
            logger.info("Medical: skipping embed/store (no chunks)")

        if med_chunks:
            logger.info("Medication: embedding via OpenAI (batched)")
            medication_pairs = await asyncio.to_thread(embed_chunks, med_chunks)
            logger.info("Medication: embedded %s vector(s)", len(medication_pairs))

            logger.info("Medication: writing to Postgres")
            await store_medication_chunks(medication_pairs)
            logger.info("Medication: store complete")
        else:
            logger.info("Medication: skipping embed/store (no chunks)")

        logger.info("Ingestion pipeline finished successfully.")
    finally:
        logger.info("Closing database pool.")
        await close_pool()


def main() -> None:
    asyncio.run(run_ingestion())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()

