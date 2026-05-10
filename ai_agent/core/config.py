"""
Central environment-backed settings for CogniCare.

Loads `.env` once; other modules import `config` rather than scattering os.getenv().
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Shared `.env` lives at CogniCare repository root (parent of `ai_agent/`).
_COGNICARE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_COGNICARE_ROOT / ".env")


# Reads one environment variable as a stripped string or None when unset/blank.
def _env(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip()
    return raw if raw else default


@dataclass(frozen=True)
class AppConfig:
    """Immutable snapshot of all supported configuration knobs."""

    # OpenAI
    openai_api_key: str | None

    # Supabase REST (memory, interaction log via supabase-py)
    supabase_url: str | None
    supabase_key: str | None

    # Direct Postgres for validated SELECT helpers (tools/db_tools)
    database_url: str | None
    supabase_db_url: str | None

    # Chroma / local RAG store
    chroma_path: str
    chroma_collection_name: str

    # Optional integrations
    web_search_api_key: str | None
    person1_api_url: str | None

    # External knowledge API (chunks only; rag_tool POSTs JSON {"query": ...})
    knowledge_base_api_url: str | None

    # Optional Bearer token for locked-down RAG endpoints
    rag_api_key: str | None

    # Models (override via env without code changes)
    intent_router_model: str
    agent_llm_model: str
    db_format_model: str


# Builds the typed config object from os.environ defaults.
def load_config() -> AppConfig:
    """Constructs AppConfig from the current environment (call after dotenv loads)."""

    chroma_collection = os.getenv("CHROMA_COLLECTION_NAME", "cognicare_knowledge").strip()

    return AppConfig(
        openai_api_key=_env("OPENAI_API_KEY"),
        supabase_url=_env("SUPABASE_URL"),
        supabase_key=_env("SUPABASE_SERVICE_ROLE_KEY"),
        database_url=_env("DATABASE_URL"),
        supabase_db_url=_env("SUPABASE_DB_URL"),
        chroma_path=_env("CHROMA_PATH") or "./chroma_store",
        chroma_collection_name=chroma_collection or "cognicare_knowledge",
        web_search_api_key=_env("WEB_SEARCH_API_KEY"),
        person1_api_url=_env("PERSON1_API_URL"),
        knowledge_base_api_url=_env("KNOWLEDGE_BASE_URL") or _env("RAG_API_URL"),
        rag_api_key=_env("RAG_API_KEY"),
        intent_router_model=_env("INTENT_ROUTER_MODEL") or "gpt-4o",
        agent_llm_model=_env("AGENT_MODEL", "gpt-4o-mini"),
        db_format_model=_env("DB_FORMAT_MODEL", "gpt-4o-mini"),
    )


config = load_config()


# Prefer explicit DATABASE_URL, then Supabase direct connection string aliases.
def postgres_dsn() -> str | None:
    """Preferred Postgres URI for raw SELECT execution (falls back gracefully)."""

    return config.database_url or config.supabase_db_url


__all__ = [
    "AppConfig",
    "config",
    "load_config",
    "postgres_dsn",
]
