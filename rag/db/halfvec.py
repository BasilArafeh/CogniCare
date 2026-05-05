"""asyncpg codec for pgvector `halfvec` (text literal form)."""

from __future__ import annotations

from typing import Sequence

import asyncpg


def _encode_halfvec_literal(value: Sequence[float]) -> str:
    if not isinstance(value, list):
        raise TypeError(
            f"halfvec encoder expects list[float], got {type(value).__name__}"
        )
    return "[" + ",".join(str(float(x)) for x in value) + "]"


def _decode_halfvec_literal(data: str) -> list[float]:
    s = data.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
    else:
        inner = s
    if not inner:
        return []
    return [float(part.strip()) for part in inner.split(",")]


async def register_halfvec_codec(
    conn: asyncpg.Connection, *, schema: str = "extensions"
) -> None:
    await conn.set_type_codec(
        "halfvec",
        schema=schema,
        encoder=_encode_halfvec_literal,
        decoder=_decode_halfvec_literal,
        format="text",
    )
