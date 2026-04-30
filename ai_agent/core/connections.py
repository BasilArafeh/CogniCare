"""
Shared singleton clients for the agent layer; import from here instead of creating new clients.

Provides OpenAI (sync + async), Supabase, optional Chroma, and config strings for RAG / Person1.
"""

import logging
from typing import Any

import openai

from core.config import config

try:
    from supabase import Client, create_client  # type: ignore[reportMissingImports]
except Exception:
    create_client = None
    Client = Any

try:
    import chromadb
except Exception:
    chromadb = None

logger = logging.getLogger(__name__)


# Creates the synchronous OpenAI API client used by LangChain tools and blocking code paths.
def _init_openai() -> openai.OpenAI:
    api_key = config.openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in .env")
    return openai.OpenAI(api_key=api_key)


# Creates the asyncio OpenAI client used by async routes such as intent classification.
def _init_async_openai() -> openai.AsyncOpenAI:
    api_key = config.openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in .env")
    return openai.AsyncOpenAI(api_key=api_key)


# Creates the Supabase client for patient data, logs, and memory tables.
def _init_supabase() -> Client:
    if create_client is None:
        raise ImportError("Missing dependency 'supabase'. Install it with: pip install supabase")
    url = config.supabase_url
    key = config.supabase_key
    if not url or not key:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY is not set in .env")
    return create_client(url, key)


# Creates a persistent Chroma store and knowledge collection for local vector RAG search.
def _init_chroma() -> tuple[Any, Any]:
    if chromadb is None:
        raise ImportError("Missing dependency 'chromadb'. Install it with: pip install chromadb")
    chroma_path = config.chroma_path
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name=config.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB ready - %s chunks loaded.", collection.count())
    return client, collection


openai_client: openai.OpenAI = _init_openai()
async_openai_client: openai.AsyncOpenAI = _init_async_openai()

try:
    supabase_client: Client | None = _init_supabase()
except Exception as e:
    logger.warning("Supabase client unavailable: %s", e)
    supabase_client = None

try:
    chroma_client, chroma_collection = _init_chroma()
except Exception as e:
    logger.warning("Chroma client unavailable: %s", e)
    chroma_client, chroma_collection = None, None

web_search_api_key: str = config.web_search_api_key or ""
if not web_search_api_key:
    logger.warning("WEB_SEARCH_API_KEY not set - web fallback will be disabled.")

person1_api_url: str = config.person1_api_url or ""
if not person1_api_url:
    logger.warning("PERSON1_API_URL not set - Person 1 routes will fail.")

__all__ = [
    "async_openai_client",
    "chroma_client",
    "chroma_collection",
    "openai_client",
    "person1_api_url",
    "supabase_client",
    "web_search_api_key",
]
