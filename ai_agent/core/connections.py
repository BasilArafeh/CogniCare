"""
agent/core/connections.py
--------------------------
Initializes all external clients once and shares them across the agent layer.
Never re-initialize clients elsewhere — always import from here.

Clients:
  - openai_client     → intent_router.py, agent_executor.py
  - supabase_client   → memory_manager.py, escalation_manager.py
  - chroma_client     → kept for admin/test operations
  - chroma_collection → rag_agent.py

Constants:
  - web_search_api_key → rag_tools.py (web_search_fallback)
  - person1_api_url    → orchestrator.py (Person 1 API calls)

Requires in .env:
  OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY,
  CHROMA_PATH, WEB_SEARCH_API_KEY, PERSON1_API_URL
"""

import os
import logging
from dotenv import load_dotenv

import openai
from supabase import create_client, Client
import chromadb

load_dotenv()
logger = logging.getLogger(__name__)


# OpenAI client — used by intent router and ReAct agent
def _init_openai() -> openai.OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in .env")
    return openai.OpenAI(api_key=api_key)


# Supabase client — used for memory and alert logging
def _init_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY is not set in .env")
    return create_client(url, key)


# ChromaDB client + collection — used by rag_agent.py for vector search
# cosine similarity space is required for BGE-M3 embeddings
def _init_chroma() -> tuple[chromadb.PersistentClient, chromadb.Collection]:
    chroma_path = os.getenv("CHROMA_PATH", "./chroma_store")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="cognicare_knowledge",
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(f"ChromaDB ready — {collection.count()} chunks loaded.")
    return client, collection


# Shared instances — import these everywhere else
openai_client: openai.OpenAI = _init_openai()
supabase_client: Client = _init_supabase()

# chroma_client kept for admin operations
chroma_client, chroma_collection = _init_chroma()

# Web search fallback — used by rag_tools.py (Tier 2 RAG)
web_search_api_key: str = os.getenv("WEB_SEARCH_API_KEY", "")
if not web_search_api_key:
    logger.warning("WEB_SEARCH_API_KEY not set — web fallback will be disabled.")

# Person 1 API base URL — used by orchestrator for patient profile routes
person1_api_url: str = os.getenv("PERSON1_API_URL", "")
if not person1_api_url:
    logger.warning("PERSON1_API_URL not set — Person 1 routes will fail.")