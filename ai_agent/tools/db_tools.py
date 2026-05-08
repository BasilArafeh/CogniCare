"""
LangChain tools for DB and DB_RAG routes.

Flow: intent router emits a SELECT/WITH → validate_sql(...) → fetch rows → format for the patient.
patient_id / name are closure-bound so the agent never supplies them manually.
Needs DATABASE_URL or SUPABASE_DB_URL and psycopg.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from core.config import config, postgres_dsn
from core.connections import openai_client
from prompts.db_prompt import DB_FORMAT_PROMPT
from tools.sql_validator import validate_sql

logger = logging.getLogger(__name__)

try:
    from langchain_core.tools import tool as lc_tool
except ImportError:

    def lc_tool(f: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[misc]
        logger.warning("langchain-core not installed; db tools stay plain functions.")
        return f


# Runs psycopg and returns rows or None when DSN/driver/unavailable or query fails after validation.
def _fetch_rows_sql(sql: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    dsn = postgres_dsn()
    if not dsn:
        return None, "Postgres URI not configured (DATABASE_URL / SUPABASE_DB_URL)."

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        return None, "Install psycopg: pip install psycopg[binary]"

    try:
        with psycopg.connect(dsn, connect_timeout=30) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return list(cur.fetchall()), None
    except Exception:
        logger.exception("DB SELECT failed")
        return None, "database error"


# Turns structured rows into one patient-facing paragraph using the shared formatter prompt.
def _naturalize(question: str, sql_result_json: str, patient_first_name: str) -> str:
    prompt = DB_FORMAT_PROMPT.format(
        patient_name=patient_first_name,
        query=question,
        sql_result=sql_result_json,
    )
    try:
        rsp = openai_client.chat.completions.create(
            model=config.db_format_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        text = (rsp.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception:
        logger.exception("DB format LLM call failed")

    return (
        f"I couldn't find that information in your records, {patient_first_name}. "
    )


def _pipeline(
    patient_id: str,
    patient_first_name: str,
    question: str,
    sql_query: str,
) -> str:
    """Validate → execute SELECT → summarize; never leaks internals."""
    sql_query = sql_query.strip()
    logger.info("Executing SQL: %s", sql_query)
    ok, err = validate_sql(sql_query, patient_id)
    if not ok:
        logger.error("SQL rejected before run: %s", err)
        return (
            f"I'm having trouble looking that up safely right now, {patient_first_name}. "
            "Your caregiver can double-check."
        )

    rows, run_err = _fetch_rows_sql(sql_query)
    if run_err:
        logger.error("Skipped or failed execution: %s", run_err)
        return (
            f"I couldn't read your records at the moment, {patient_first_name}. "
            "Let's ask your caregiver to help."
        )

    blob = json.dumps(rows or [], default=str, indent=2) if rows is not None else "[]"
    return _naturalize(question, blob, patient_first_name)


# Builds LangChain tools bound to the active patient (used by executor for DB / DB_RAG intents).
def create_database_tools(
    patient_id: str,
    patient_first_name: str,
    sql_query: str,
) -> list[Any]:
    """
    Returns tools for the ReAct loop. Primary entry: pass intent-router SQL + the user question.

    The orchestrator/agent should plug in sql_query from routing output for DB and DB_RAG turns.
    """
    pid = patient_id.strip()
    name = patient_first_name.strip()
    routed_sql = (sql_query or "").strip()

    @lc_tool
    def query_personal_health_data(question: str) -> str:
        """
        Run the authorized SELECT/WITH SELECT for this patient using SQL from intent routing.

        Args:
          question: The patient's wording (for tone in the formatter).

        SQL is closure-bound from orchestration routing metadata; the tool only needs the question.
        """
        logger.info("query_personal_health_data tool patient_id=%s", pid)
        if not routed_sql:
            logger.error("query_personal_health_data missing routed SQL patient_id=%s", pid)
            return (
                f"I'm having trouble looking that up safely right now, {name}. "
                "Your caregiver can double-check."
            )
        return _pipeline(pid, name, question.strip(), routed_sql)

    return [query_personal_health_data]


__all__ = ["create_database_tools"]
