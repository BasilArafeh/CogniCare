"""Prompt templates for classifier, agent, DB/RAG formatting, and LLM-only turns."""

from .agent_prompt import AGENT_PROMPT
from .db_prompt import DB_FORMAT_PROMPT
from .intent_prompt import INTENT_ROUTER_PROMPT
from .llm_prompt import LLM_PROMPT
from .rag_prompt import RAG_FORMAT_PROMPT

__all__ = [
    "AGENT_PROMPT",
    "DB_FORMAT_PROMPT",
    "INTENT_ROUTER_PROMPT",
    "LLM_PROMPT",
    "RAG_FORMAT_PROMPT",
]
