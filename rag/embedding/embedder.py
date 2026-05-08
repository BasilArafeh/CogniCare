from __future__ import annotations

import logging
import time

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from rag.chunking.schemas import MedicalChunk, MedicationChunk
from rag.config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_BATCH_SLEEP_SEC,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MAX_RETRIES,
    OPENAI_EMBEDDING_MODEL,
)

logger = logging.getLogger(__name__)

_chunk_t = MedicalChunk | MedicationChunk


@retry(
    stop=stop_after_attempt(EMBEDDING_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=120),
)
def _embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=texts,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    ordered = sorted(response.data, key=lambda row: row.index)
    return [list(row.embedding) for row in ordered]


def embed_chunks(chunks: list[_chunk_t]) -> list[tuple[_chunk_t, list[float]]]:
    """Embed only ``chunk.text``; return chunks paired with embedding vectors."""
    if not chunks:
        return []

    client = OpenAI()
    out: list[tuple[_chunk_t, list[float]]] = []

    batch_size = EMBEDDING_BATCH_SIZE
    batch_count = (len(chunks) + batch_size - 1) // batch_size

    for batch_num in range(1, batch_count + 1):
        start = (batch_num - 1) * batch_size
        batch = chunks[start : start + batch_size]
        texts = [c.text for c in batch]
        try:
            vectors = _embed_batch(client, texts)
            out.extend(zip(batch, vectors, strict=True))
            logger.info(
                "Embedding batch %s/%s: %s chunks, success",
                batch_num,
                batch_count,
                len(batch),
            )
        except Exception:
            logger.exception(
                "Embedding batch %s/%s: %s chunks, failure",
                batch_num,
                batch_count,
                len(batch),
            )
            raise

        if start + batch_size < len(chunks):
            time.sleep(EMBEDDING_BATCH_SLEEP_SEC)

    return out
