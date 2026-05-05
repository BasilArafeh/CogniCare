from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from rag.config import RERANKER_MODEL, RETRIEVAL_FINAL_K

logger = logging.getLogger(__name__)

_encoder: Any | None = None


def _cross_encoder() -> Any:
    """Lazily load CrossEncoder so importing retrieval does not require torch/tf at import time."""
    global _encoder
    if _encoder is None:
        # Optional `tf-keras`/`tensorflow` installs still register loggers — keep stderr quiet.
        for _noise in ("tensorflow", "absl", "transformers"):
            logging.getLogger(_noise).setLevel(logging.ERROR)

        try:
            import torch

            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
        except (ImportError, RuntimeError):
            pass

        from sentence_transformers import CrossEncoder

        _encoder = CrossEncoder(RERANKER_MODEL, device="cpu")
    return _encoder


def rerank(query: str, chunks: list["RetrievedChunk"]) -> list["RetrievedChunk"]:
    """Score (query, chunk.text) pairs; return top ``RETRIEVAL_FINAL_K`` by descending score."""

    if not chunks:
        return []

    encoder = _cross_encoder()
    pairs = [[query, c.text] for c in chunks]
    scores_arr = encoder.predict(pairs)

    enriched: list[tuple[Any, float]] = []
    for chunk, raw in zip(chunks, scores_arr, strict=True):
        score = float(raw)
        logger.debug(
            "rerank score=%s source=%s text_preview=%s",
            score,
            chunk.source,
            (chunk.text[:120] + "…") if len(chunk.text) > 120 else chunk.text,
        )
        enriched.append((replace(chunk, score=score), score))

    enriched.sort(key=lambda item: item[1], reverse=True)
    return [c for c, _ in enriched[:RETRIEVAL_FINAL_K]]
