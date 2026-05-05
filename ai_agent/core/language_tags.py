"""Normalize language tags from API clients for prompts and fallbacks."""

from __future__ import annotations


def normalize_primary_language(language: str | None, *, default: str = "en") -> str:
    """
    Returns the primary subtag lowercased (e.g. en-US -> en, AR -> ar).

    Used so AGENT_PROMPT / LLM_PROMPT {language} placeholders match the ar/en rules.
    """

    raw = (default if language is None else str(language)).strip()
    if not raw:
        raw = default.strip() or "en"
    primary = raw.split("-", 1)[0].strip().lower()
    return primary if primary else (default.strip().lower() or "en")


__all__ = ["normalize_primary_language"]
