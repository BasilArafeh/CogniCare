"""Single-turn RAG: retrieve reranked chunks, then generate an answer."""

from __future__ import annotations

import asyncio

from rag.generation.generator import GenerationResult, generate_answer
from rag.retrieval import RetrievalTarget, retrieve_for_generation_auto


async def run_rag_turn(
    query: str,
    target: RetrievalTarget,
    *,
    medication_search_term: str | None = None,
    medical_source_folder: str | None = None,
) -> GenerationResult:
    chunks = await retrieve_for_generation_auto(
        query=query,
        target=target,
        medication_search_term=medication_search_term,
        medical_source_folder=medical_source_folder,
    )
    return await asyncio.to_thread(generate_answer, query, chunks)
