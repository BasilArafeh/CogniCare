"""
Exercise the full RAG path: retrieve → rerank → generate (needs DB + OpenAI).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from rag.rag_turn import run_rag_turn
from rag.retrieval import RetrievalTarget


def _source_labels(sources: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for meta in sources:
        gn = meta.get("generic_name")
        fn = meta.get("filename")
        if gn:
            out.append(str(gn))
        elif fn:
            out.append(str(fn))
        else:
            out.append("(no filename / generic_name)")
    return out


async def main() -> None:
    medical_query = "What are the late stage symptoms of Alzheimer's?"
    med_result = await run_rag_turn(
        query=medical_query,
        target=RetrievalTarget.MEDICAL,
    )
    print("Query:", medical_query)
    print("Answer:", med_result.answer)
    print("Sources (filename or generic_name):", _source_labels(med_result.sources))

    rx_query = "What are the warnings for acetaminophen?"
    rx_result = await run_rag_turn(
        query=rx_query,
        target=RetrievalTarget.MEDICATIONS,
        medication_search_term="acetaminophen",
    )
    print()
    print("Query:", rx_query)
    print("Answer:", rx_result.answer)
    print("Sources (filename or generic_name):", _source_labels(rx_result.sources))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
