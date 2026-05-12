"""
LangChain tool: embed the patient question, fetch top‑3 chunks via Supabase pgvector RPC,
then format a short reply with OpenAI using the shared RAG prompt.

Requires a Postgres RPC (exposed via PostgREST) whose required args are ``query_embedding`` and
``match_count`` (optional ``filter_source_type``, ``filter_field_type``, ``filter_source_id`` may exist
with defaults). Returns rows with a ``content`` text column — e.g. against
``medical_documents.embedding`` (halfvec):

    create or replace function public.match_medical_documents(
        query_embedding extensions.halfvec(3072),
        match_count int default 3
    )
    returns table (content text)
    language sql stable
    as $$
      select md.content::text
      from public.medical_documents md
      order by md.embedding <=> query_embedding
      limit least(coalesce(match_count, 3), 100);
    $$;

RPC name defaults to ``match_medical_documents``; override with env ``RAG_VECTOR_MATCH_RPC``.
On any retrieval, RPC, embedding, or formatting failure → ``FALLBACK_TEXT``.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from core.config import config
from core.connections import openai_client, supabase_client
from prompts.rag_prompt import RAG_PROMPT

import logging

logger = logging.getLogger(__name__)

try:
    from langchain_core.tools import tool as lc_tool
except ImportError:

    def lc_tool(f: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[misc]
        logger.warning("langchain-core not installed; RAG tool stays a plain function.")
        return f


# Same default copy as legacy HTTP stack when nothing useful returns.
FALLBACK_TEXT = "No reference material is available for this question right now."

_EMBEDDING_MODEL = "text-embedding-3-large"
_RPC_NAME_ENV = "RAG_VECTOR_MATCH_RPC"


# Returns Postgres RPC used for similarity search (defaults to match_medical_documents).
def _match_rpc_name() -> str:
    return (os.getenv(_RPC_NAME_ENV) or "").strip() or "match_medical_documents"


# Sync OpenAI embeddings for query text; None on failure.
def _embed_query(question: str) -> list[float] | None:
    try:
        resp = openai_client.embeddings.create(
            model=_EMBEDDING_MODEL,
            input=[question.strip()],
        )
        ordered = sorted(resp.data, key=lambda row: row.index)
        return list(ordered[0].embedding)
    except Exception:
        logger.exception("RAG embedding failed")
        return None


# Calls Supabase RPC matching ``query_embedding`` + ``match_count`` (optional filter_* use DB defaults).
def _rpc_match_contents(query_embedding: list[float], match_count: int = 3) -> list[str]:
    if supabase_client is None:
        logger.warning("Supabase client not configured; skipping vector match")
        return []
    rpc = _match_rpc_name()
    rpc_params = {
        "query_embedding": query_embedding,
        "match_count": match_count,
        # filter_source_type, filter_field_type, filter_source_id omitted — server defaults apply.
    }
    try:
        res = supabase_client.rpc(rpc, rpc_params).execute()
    except Exception:
        logger.exception("Supabase RPC '%s' failed", rpc)
        return []

    data = getattr(res, "data", None)
    if not data:
        return []

    out: list[str] = []
    for row in data:
        if isinstance(row, str):
            text = row.strip()
        elif isinstance(row, dict):
            raw = row.get("content")
            text = str(raw).strip() if raw is not None else ""
        else:
            text = ""
        if text:
            out.append(text)
    return out[:match_count]


# Same pattern as db_tools._naturalize: format prompt → OpenAI completion with db_format_model.
def _naturalize(question: str, chunks_blob: str) -> str:
    prompt = RAG_PROMPT.format(query=question, chunks=chunks_blob)
    try:
        rsp = openai_client.chat.completions.create(
            model=config.db_format_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        text = (rsp.choices[0].message.content or "").strip()
        return text if text else FALLBACK_TEXT
    except Exception:
        logger.exception("RAG format LLM call failed")

    return FALLBACK_TEXT


# End‑to‑end: embed → pgvector RPC top‑3 → naturalize via LLM; any gap → FALLBACK_TEXT.
def _retrieve(question: str) -> str:
    q = question.strip()
    if not q:
        return FALLBACK_TEXT

    embedding = _embed_query(q)
    if embedding is None:
        logger.error("RAG retrieve failed: embedding returned None for question=%r", q)
        return FALLBACK_TEXT

    contents = _rpc_match_contents(embedding, match_count=3)
    logger.info("RAG chunks retrieved: %s for question=%r", len(contents), q)
    if not contents:
        logger.warning("RAG retrieve: RPC returned 0 chunks for question=%r", q)
        return FALLBACK_TEXT

    blob = "\n\n".join(c for c in contents if c.strip())
    if not blob.strip():
        return FALLBACK_TEXT

    logger.debug("RAG RPC returned %s chunk(s)", len(contents))
    return _naturalize(q, blob)


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
