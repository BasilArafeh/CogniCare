"""
LangChain tool: POST the user question to our RAG HTTP API and return retrieved text.

Contract: response body is JSON exactly `{"chunks": [{"content": str, "score": float}, ...]}`.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Callable

from core.config import config

logger = logging.getLogger(__name__)

try:
    from langchain_core.tools import tool as lc_tool
except ImportError:

    def lc_tool(f: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[misc]
        logger.warning("langchain-core not installed; RAG tool stays a plain function.")
        return f

# Returned when the URL is missing, the request fails, or the body does not match the contract.
FALLBACK_TEXT = "No reference material is available for this question right now."


# Validates and extracts (content, score) rows; None if the payload is not exactly the expected shape.
def _parse_rag_response(payload: Any) -> list[tuple[str, float]] | None:
    if not isinstance(payload, dict):
        return None
    rows = payload.get("chunks")
    if not isinstance(rows, list):
        return None

    parsed: list[tuple[str, float]] = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        content = row.get("content")
        score = row.get("score")
        if not isinstance(content, str) or not isinstance(score, (int, float)):
            return None
        text = content.strip()
        if text:
            parsed.append((text, float(score)))

    return parsed


# POST {"query": ...} and return parsed chunks or None.
def _request_rag(query: str, timeout_sec: float = 30.0) -> list[tuple[str, float]] | None:
    base = (config.knowledge_base_api_url or "").strip()
    if not base:
        logger.warning("RAG URL not set (KNOWLEDGE_BASE_URL / RAG_API_URL)")
        return None

    body = json.dumps({"query": query.strip()}).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/"),
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    if config.rag_api_key:
        req.add_header("Authorization", f"Bearer {config.rag_api_key.strip()}")

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        logger.error("RAG HTTP %s %s", e.code, e.reason)
        return None
    except urllib.error.URLError as e:
        logger.error("RAG URL error: %s", e.reason)
        return None
    except Exception:
        logger.exception("RAG request failed")
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("RAG response not JSON: %s", raw[:200])
        return None

    chunks = _parse_rag_response(data)
    if chunks is None:
        logger.warning("RAG response did not match strict chunks contract")
        return None
    return chunks


# Top 3 by score descending; join contents into one block.
def _chunks_to_text(chunks: list[tuple[str, float]]) -> str:
    ranked = sorted(chunks, key=lambda x: x[1], reverse=True)[:3]
    return "\n\n".join(text for text, _ in ranked)


# Runs retrieval; any problem yields FALLBACK_TEXT.
def _retrieve(question: str) -> str:
    q = question.strip()
    if not q:
        return FALLBACK_TEXT

    chunks = _request_rag(q)
    if not chunks:
        return FALLBACK_TEXT

    block = _chunks_to_text(chunks)
    if not block:
        return FALLBACK_TEXT

    logger.info("RAG ok: %s chunk(s) used after top-3 trim", min(3, len(chunks)))
    return block


@lc_tool
def search_knowledge_base(question: str) -> str:
    """
    Search the approved caregiving knowledge base (not personal medical records).

    Ground answers only in the returned text; do not invent clinical facts.
    """

    logger.info("search_knowledge_base len=%s", len(question or ""))
    return _retrieve(question)


def create_rag_tools() -> list[Any]:
    """Single-tool list for RAG / DB_RAG routes."""

    return [search_knowledge_base]


__all__ = ["create_rag_tools", "search_knowledge_base"]
