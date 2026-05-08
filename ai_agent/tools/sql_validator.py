"""
Light guardrail for SQL emitted by the intent-router LLM (not end-user SQL).

Checks: single read statement (SELECT / WITH … SELECT), no obvious write DDL/DML tokens,
only allow-listed tables after FROM/JOIN, and `patient_id = <session id>`.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

BLACKLISTED_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
    "TRUNCATE", "CREATE", "EXEC", "EXECUTE", "GRANT",
    "REVOKE", "MERGE", "CALL", "EXPLAIN",
}

ALLOWED_TABLES = {
    "patients",
    "patient_medications",
    "patient_meals",
    "patient_activities",
    "patient_memory",
    "medication",
    "meals",
    "activity",
    "caregiver",
    "caregiver_priority",
    "family_member",
    "reminders",
    "alerts",
}

RE_FROM_TABLE = re.compile(
    r"\b(?:FROM|JOIN)\s+(?:(?:\w+)\.)?(?P<t>[a-zA-Z_]\w*)\b",
    re.I,
)


def _block(reason: str, sql: str | None = None) -> tuple[bool, str]:
    """Log rejection and return (False, reason) for callers."""
    if sql is not None:
        logger.error("SQL validator: %s | sql=%s", reason, sql)
    else:
        logger.error("SQL validator: %s", reason)
    return False, reason


def validate_sql(sql: str, patient_id: str) -> tuple[bool, str | None]:
    pid = str(patient_id).strip()
    if not pid:
        return _block("patient_id is empty.")

    sql = (sql or "").strip()
    if not sql:
        return _block("SQL query is empty.")

    u = sql.upper()
    core = u.rstrip(";")
    if ";" in core:
        return _block("Multiple statements forbidden.", sql)

    trimmed = u.lstrip()
    if not (trimmed.startswith("SELECT") or (trimmed.startswith("WITH") and "SELECT" in u)):
        return _block("Only SELECT or WITH … SELECT allowed.", sql)

    tokens = set(re.findall(r"\b[A-Z_]+\b", u)) & BLACKLISTED_KEYWORDS
    if tokens:
        return _block(f"Bad keyword(s): {tokens}", sql)

    joins = {m.group("t").lower() for m in RE_FROM_TABLE.finditer(sql)}
    cte_aliases = {x.lower() for x in re.findall(r"\bWITH\s+(?:RECURSIVE\s+)?(\w+)\s+AS\s*\(", sql, re.I)}
    cte_aliases |= {x.lower() for x in re.findall(r",\s*(\w+)\s+AS\s*\(", sql, re.I)}
    tables = joins - cte_aliases

    if not tables:
        return _block("Need at least one table after FROM/JOIN.", sql)

    rogue = tables - ALLOWED_TABLES
    if rogue:
        return _block(f"Table(s) not allowed: {rogue}", sql)

    if not re.search(rf"patient_id\s*=\s*{re.escape(pid)}\b", sql, re.I):
        return _block(f"Missing patient_id = {pid}", sql)

    logger.info("SQL ok patient_id=%s sql=%s", pid, sql)
    return True, None


__all__ = ["ALLOWED_TABLES", "BLACKLISTED_KEYWORDS", "validate_sql"]
