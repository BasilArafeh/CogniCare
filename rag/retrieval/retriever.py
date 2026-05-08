from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Callable, Literal

from openai import OpenAI
from rank_bm25 import BM25Okapi

from rag.config import (
    BM25_WEIGHT,
    EMBEDDING_DIMENSIONS,
    HYBRID_SEARCH_ENABLED,
    OPENAI_EMBEDDING_MODEL,
    RETRIEVAL_INITIAL_K,
    VECTOR_WEIGHT,
)
from rag.db.db import get_connection

from .reranker import rerank

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievedChunk:
    """One retrieval hit before/after reranking."""

    text: str
    score: float
    source: Literal["medical", "medication"]
    metadata: dict[str, Any]


class RetrievalTarget(str, Enum):
    MEDICAL = "medical"
    MEDICATIONS = "medications"


# --- BM25 corpus cache (per table / filter key) ---
@dataclass(slots=True)
class _MedicalBm25Index:
    tokenized: list[list[str]]
    row_dicts: list[dict[str, Any]]
    bm25: BM25Okapi | None


@dataclass(slots=True)
class _MedicationBm25Index:
    tokenized: list[list[str]]
    row_dicts: list[dict[str, Any]]
    bm25: BM25Okapi | None


_MEDICAL_BM25_KEY_ALL = "__medical_all__"
_MEDICATION_BM25_KEY_ALL = "__medication_all__"
_MEDICATION_BM25_KEY_EMPTY = "__medication_empty_search__"


_medical_bm25_cache: dict[str, _MedicalBm25Index] = {}
_medication_bm25_cache: dict[str, _MedicationBm25Index] = {}
_bm25_cache_lock = asyncio.Lock()


def _tokenize_bm25(text: str) -> list[str]:
    return text.lower().split()


def _embed_query_sync(query: str) -> list[float]:
    client = OpenAI()
    resp = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=[query],
        dimensions=EMBEDDING_DIMENSIONS,
    )
    ordered = sorted(resp.data, key=lambda row: row.index)
    return list(ordered[0].embedding)


def _medical_key_from_meta(meta: dict[str, Any]) -> tuple[Any, ...]:
    return (meta["source_folder"], meta["filename"], meta["chunk_index"])


def _medication_key_from_meta(meta: dict[str, Any]) -> tuple[Any, ...]:
    return (meta["generic_name"], meta["chunk_index"], meta["chunk_type"])


def _row_to_medical_chunk(row: Any, *, score: float) -> RetrievedChunk:
    meta = {
        "content": row["content"],
        "source_folder": row["source_folder"],
        "filename": row["filename"],
        "page_number": row["page_number"],
        "section_title": row["section_title"],
        "chunk_index": row["chunk_index"],
    }
    return RetrievedChunk(
        text=row["content"],
        score=score,
        source="medical",
        metadata=meta,
    )


def _row_to_medication_chunk(row: Any, *, score: float) -> RetrievedChunk:
    meta = {
        "content": row["content"],
        "generic_name": row["generic_name"],
        "brand_names": row["brand_names"],
        "drug_class": row["drug_class"],
        "manufacturer": row["manufacturer"],
        "chunk_type": row["chunk_type"],
        "chunk_index": row["chunk_index"],
    }
    return RetrievedChunk(
        text=row["content"],
        score=score,
        source="medication",
        metadata=meta,
    )


async def _ensure_medical_bm25_index(
    conn: Any,
    source_folder: str | None,
) -> _MedicalBm25Index:
    cache_key = _MEDICAL_BM25_KEY_ALL if source_folder is None else source_folder
    async with _bm25_cache_lock:
        hit = _medical_bm25_cache.get(cache_key)
        if hit is not None:
            return hit

        if source_folder is None:
            rows = await conn.fetch(
                """
                SELECT content,
                       source_folder,
                       filename,
                       page_number,
                       section_title,
                       chunk_index
                FROM medical_documents
                """
            )
        else:
            rows = await conn.fetch(
                """
                SELECT content,
                       source_folder,
                       filename,
                       page_number,
                       section_title,
                       chunk_index
                FROM medical_documents
                WHERE source_folder = $1
                """,
                source_folder,
            )

        row_dicts = [dict(r) for r in rows]
        tokenized = [_tokenize_bm25(r["content"]) for r in row_dicts]
        if not tokenized:
            idx = _MedicalBm25Index(tokenized=[], row_dicts=[], bm25=None)
        else:
            idx = _MedicalBm25Index(
                tokenized=tokenized,
                row_dicts=row_dicts,
                bm25=BM25Okapi(tokenized),
            )
        _medical_bm25_cache[cache_key] = idx
        logger.info(
            "BM25 index built for medical_documents (folder=%s, rows=%s)",
            source_folder,
            len(row_dicts),
        )
        return idx


async def _ensure_medication_bm25_index(
    conn: Any,
    search_term: str | None,
) -> _MedicationBm25Index:
    if search_term is None:
        cache_key = _MEDICATION_BM25_KEY_ALL
    else:
        lowered = search_term.strip().lower()
        cache_key = lowered if lowered else _MEDICATION_BM25_KEY_EMPTY

    async with _bm25_cache_lock:
        hit = _medication_bm25_cache.get(cache_key)
        if hit is not None:
            return hit

        if search_term is None:
            rows = await conn.fetch(
                """
                SELECT content,
                       generic_name,
                       brand_names,
                       drug_class,
                       manufacturer,
                       chunk_type,
                       chunk_index
                FROM medication_documents
                """
            )
        else:
            rows = await conn.fetch(
                """
                SELECT content,
                       generic_name,
                       brand_names,
                       drug_class,
                       manufacturer,
                       chunk_type,
                       chunk_index
                FROM medication_documents
                WHERE generic_name ILIKE $1
                   OR ($2 ILIKE ANY (COALESCE(brand_names, ARRAY[]::text[])))
                """,
                search_term,
                search_term,
            )

        row_dicts = [dict(r) for r in rows]
        tokenized = [_tokenize_bm25(r["content"]) for r in row_dicts]
        if not tokenized:
            idx = _MedicationBm25Index(tokenized=[], row_dicts=[], bm25=None)
        else:
            idx = _MedicationBm25Index(
                tokenized=tokenized,
                row_dicts=row_dicts,
                bm25=BM25Okapi(tokenized),
            )
        _medication_bm25_cache[cache_key] = idx
        logger.info(
            "BM25 index built for medication_documents (cache_key=%s, rows=%s)",
            cache_key,
            len(row_dicts),
        )
        return idx


def _bm25_top_medical(index: _MedicalBm25Index, query: str, k: int) -> list[RetrievedChunk]:
    if not index.row_dicts or not index.tokenized or index.bm25 is None:
        return []
    qtok = _tokenize_bm25(query)
    scores = index.bm25.get_scores(qtok)
    n = len(scores)
    order = sorted(range(n), key=lambda i: scores[i], reverse=True)[:k]
    return [
        _row_to_medical_chunk(index.row_dicts[i], score=float(scores[i])) for i in order
    ]


def _bm25_top_medication(index: _MedicationBm25Index, query: str, k: int) -> list[RetrievedChunk]:
    if not index.row_dicts or not index.tokenized or index.bm25 is None:
        return []
    qtok = _tokenize_bm25(query)
    scores = index.bm25.get_scores(qtok)
    n = len(scores)
    order = sorted(range(n), key=lambda i: scores[i], reverse=True)[:k]
    return [
        _row_to_medication_chunk(index.row_dicts[i], score=float(scores[i])) for i in order
    ]


def _weighted_rrf_fuse(
    vector_ranked: list[RetrievedChunk],
    bm25_ranked: list[RetrievedChunk],
    *,
    key_fn: Callable[[RetrievedChunk], tuple[Any, ...]],
    vector_weight: float,
    bm25_weight: float,
    top_n: int,
) -> list[RetrievedChunk]:
    """Fuse two ranked lists using weighted reciprocal-rank contributions."""
    vec_ranks: dict[tuple[Any, ...], int] = {}
    for i, ch in enumerate(vector_ranked):
        vec_ranks[key_fn(ch)] = i + 1

    bm25_ranks: dict[tuple[Any, ...], int] = {}
    for i, ch in enumerate(bm25_ranked):
        bm25_ranks[key_fn(ch)] = i + 1

    best_chunk: dict[tuple[Any, ...], RetrievedChunk] = {}
    for ch in vector_ranked:
        best_chunk[key_fn(ch)] = ch
    for ch in bm25_ranked:
        k = key_fn(ch)
        if k not in best_chunk:
            best_chunk[k] = ch

    candidates = set(vec_ranks) | set(bm25_ranks)
    fused_scores: list[tuple[float, tuple[Any, ...]]] = []
    for key in candidates:
        s = 0.0
        if key in vec_ranks:
            s += vector_weight / vec_ranks[key]
        if key in bm25_ranks:
            s += bm25_weight / bm25_ranks[key]
        fused_scores.append((s, key))
    fused_scores.sort(key=lambda x: (-x[0], x[1]))

    out: list[RetrievedChunk] = []
    for fusion_score, key in fused_scores[:top_n]:
        base = best_chunk[key]
        out.append(replace(base, score=float(fusion_score)))
    return out


async def _medical_vector_chunks(
    conn: Any,
    vec: list[float],
    source_folder: str | None,
    k: int,
) -> list[RetrievedChunk]:
    if source_folder is None:
        rows = await conn.fetch(
            """
            SELECT content,
                   source_folder,
                   filename,
                   page_number,
                   section_title,
                   chunk_index,
                   (1 - (embedding <=> $1::halfvec)) AS score
            FROM medical_documents
            ORDER BY embedding <=> $1::halfvec ASC
            LIMIT $2::int
            """,
            vec,
            k,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT content,
                   source_folder,
                   filename,
                   page_number,
                   section_title,
                   chunk_index,
                   (1 - (embedding <=> $1::halfvec)) AS score
            FROM medical_documents
            WHERE source_folder = $2
            ORDER BY embedding <=> $1::halfvec ASC
            LIMIT $3::int
            """,
            vec,
            source_folder,
            k,
        )
    out: list[RetrievedChunk] = []
    for row in rows:
        out.append(_row_to_medical_chunk(row, score=float(row["score"])))
    return out


async def _medication_vector_chunks(
    conn: Any,
    vec: list[float],
    search_term: str | None,
    k: int,
) -> list[RetrievedChunk]:
    if search_term is None:
        rows = await conn.fetch(
            """
            SELECT content,
                   generic_name,
                   brand_names,
                   drug_class,
                   manufacturer,
                   chunk_type,
                   chunk_index,
                   (1 - (embedding <=> $1::halfvec)) AS score
            FROM medication_documents
            ORDER BY embedding <=> $1::halfvec ASC
            LIMIT $2::int
            """,
            vec,
            k,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT content,
                   generic_name,
                   brand_names,
                   drug_class,
                   manufacturer,
                   chunk_type,
                   chunk_index,
                   (1 - (embedding <=> $1::halfvec)) AS score
            FROM medication_documents
            WHERE generic_name ILIKE $2
               OR ($3 ILIKE ANY (COALESCE(brand_names, ARRAY[]::text[])))
            ORDER BY embedding <=> $1::halfvec ASC
            LIMIT $4::int
            """,
            vec,
            search_term,
            search_term,
            k,
        )
    out: list[RetrievedChunk] = []
    for row in rows:
        out.append(_row_to_medication_chunk(row, score=float(row["score"])))
    return out


async def retrieve_medical(
    query: str,
    source_folder: str | None = None,
) -> list[RetrievedChunk]:
    vec = await asyncio.to_thread(_embed_query_sync, query)
    k = RETRIEVAL_INITIAL_K
    async with get_connection() as conn:
        chunks_vec = await _medical_vector_chunks(conn, vec, source_folder, k)

        if not HYBRID_SEARCH_ENABLED:
            chunks = chunks_vec
        else:
            bundle = await _ensure_medical_bm25_index(conn, source_folder)
            bm25_chunks = _bm25_top_medical(bundle, query, k)
            if not bm25_chunks and not bundle.row_dicts:
                chunks = chunks_vec
            else:
                chunks = _weighted_rrf_fuse(
                    chunks_vec,
                    bm25_chunks,
                    key_fn=lambda c: _medical_key_from_meta(c.metadata),
                    vector_weight=VECTOR_WEIGHT,
                    bm25_weight=BM25_WEIGHT,
                    top_n=k,
                )

    logger.debug("retrieve_medical returned %s chunks", len(chunks))
    return chunks


async def retrieve_medication(
    query: str,
    search_term: str | None = None,
) -> list[RetrievedChunk]:
    vec = await asyncio.to_thread(_embed_query_sync, query)
    k = RETRIEVAL_INITIAL_K
    async with get_connection() as conn:
        chunks_vec = await _medication_vector_chunks(conn, vec, search_term, k)

        if not HYBRID_SEARCH_ENABLED:
            chunks = chunks_vec
        else:
            bundle = await _ensure_medication_bm25_index(conn, search_term)
            bm25_chunks = _bm25_top_medication(bundle, query, k)
            if not bm25_chunks and not bundle.row_dicts:
                chunks = chunks_vec
            else:
                chunks = _weighted_rrf_fuse(
                    chunks_vec,
                    bm25_chunks,
                    key_fn=lambda c: _medication_key_from_meta(c.metadata),
                    vector_weight=VECTOR_WEIGHT,
                    bm25_weight=BM25_WEIGHT,
                    top_n=k,
                )

    logger.debug("retrieve_medication returned %s chunks", len(chunks))
    return chunks


async def retrieve_for_generation_auto(
    query: str,
    target: RetrievalTarget,
    medication_search_term: str | None = None,
    medical_source_folder: str | None = None,
) -> list[RetrievedChunk]:
    if target is RetrievalTarget.MEDICAL:
        chunks = await retrieve_medical(query, medical_source_folder)
    elif target is RetrievalTarget.MEDICATIONS:
        chunks = await retrieve_medication(query, medication_search_term)
    else:
        raise ValueError(f"Unsupported retrieval target: {target!r}")

    return await asyncio.to_thread(rerank, query, chunks)
