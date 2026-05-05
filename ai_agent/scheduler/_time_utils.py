"""Parse Postgres TIME or timestamptz-style values from Supabase JSON for daily cron slots."""

from __future__ import annotations


# Extracts clock hour/minute from ``09:30:00``, ``09:30``, or ``2026-04-30T14:05:00+00:00``.
def hour_minute_from_db_time(value: object) -> tuple[int, int] | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if "T" in s:
        s = s.split("T", 1)[1]
    s = s.split("+", 1)[0].rstrip("Z")
    if "." in s:
        s = s.split(".", 1)[0]
    parts = s.split(":")
    try:
        h = int(parts[0])
        m = int(parts[1])
    except (IndexError, ValueError):
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return h, m


__all__ = ["hour_minute_from_db_time"]
