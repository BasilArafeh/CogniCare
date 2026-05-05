from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from rag.config import GENERATION_MODEL, GENERATION_TEMPERATURE
from .prompt_builder import build_prompt
from rag.retrieval.retriever import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GenerationResult:
    answer: str
    sources: list[dict[str, Any]]


def generate_answer(query: str, chunks: list[RetrievedChunk]) -> GenerationResult:
    messages = build_prompt(query, chunks)
    client = OpenAI()

    completion = client.chat.completions.create(
        model=GENERATION_MODEL,
        temperature=GENERATION_TEMPERATURE,
        messages=messages,
    )

    raw = completion.choices[0].message.content or ""
    answer = raw.strip()
    sources = [copy.deepcopy(c.metadata) for c in chunks]

    logger.info(
        "generation complete model=%s query_preview=%s chunks_used=%s answer_len=%s",
        GENERATION_MODEL,
        query[:160] + ("…" if len(query) > 160 else ""),
        len(chunks),
        len(answer),
    )

    return GenerationResult(answer=answer, sources=sources)
