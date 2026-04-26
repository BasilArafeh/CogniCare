"""
web_fallback.py  —  CogniCare Web Fallback Module
==================================================

Provides a trusted government/medical source web search fallback
for when local ChromaDB chunks don't contain the answer.

Used by:
  - cognicare_eval.py  (evaluation pipeline)
  - Your actual CogniCare app (any query handler)

Trusted sources searched:
  - fda.gov          — official FDA drug labels
  - medlineplus.gov  — NIH patient-friendly drug info
  - nih.gov          — National Institutes of Health
  - nhs.uk           — UK National Health Service
  - drugs.com        — comprehensive drug database

Requires: openai >= 1.66.0 (web_search_preview tool)
"""

from dataclasses import dataclass
from openai import OpenAI

# ── TRUSTED SOURCES ────────────────────────────────────────────────────────────
TRUSTED_DOMAINS = [
    "fda.gov",
    "medlineplus.gov",
    "nih.gov",
    "nhs.uk",
    "drugs.com",
    "mayoclinic.org",
]

# ── FALLBACK TRIGGER PHRASES ───────────────────────────────────────────────────
# These are exact phrases the LLM outputs when local context has no answer.
# Only trigger fallback on explicit "not in context" statements.
FALLBACK_TRIGGERS = [
    "this information is not available in the provided context",
    "the context does not provide specific information",
    "the context does not provide information",
    "the context does not contain",
    "the context does not specify",
    "not mentioned in the context",
    "no information available",
    "cannot find this information",
    "not found in the context",
    "the provided context does not",
    "is not available in the provided",
]

# ── WEB SEARCH SYSTEM PROMPT ───────────────────────────────────────────────────
_WEB_SEARCH_SYSTEM = """\
You are a clinical medical assistant with access to trusted medical websites.

Search for the answer to the question using ONLY these trusted sources:
FDA (fda.gov), MedlinePlus (medlineplus.gov), NIH (nih.gov),
NHS (nhs.uk), or Drugs.com (drugs.com).

Rules:
1. Search for the specific drug and topic in the question.
2. Use ONLY information from the trusted sources above.
3. Answer in 2-4 clear sentences.
4. Include the drug brand name and generic name.
5. If sources conflict, prefer the FDA source.
6. Do not add information beyond what the sources provide.
7. End your answer with the source in brackets: [Source: medlineplus.gov]\
"""


# ── RESULT DATACLASS ───────────────────────────────────────────────────────────
@dataclass
class FallbackResult:
    answer:        str
    used_fallback: bool
    source:        str        # "local", "web", "web_empty", or "error"
    source_url:    str | None


# ── MAIN CLASS ─────────────────────────────────────────────────────────────────
class WebFallback:
    """
    Web search fallback for the CogniCare RAG pipeline.

    Parameters
    ----------
    client : OpenAI
        Authenticated OpenAI client (reused from pipeline, no extra connections).
    model : str
        Model for web search. Must support web_search_preview.
        Default: gpt-4o-mini (cheap, sufficient for factual lookup).
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model  = model

    # ── PUBLIC: check if fallback needed ──────────────────────────────────────
    def needs_fallback(self, answer: str) -> bool:
        """
        Returns True if the local answer signals missing context.
        Only fires on explicit "not in context" phrases — never on
        partial or imperfect answers.
        """
        answer_lower = answer.lower().strip()

        # Too short to be a real medical answer
        if len(answer_lower) < 30:
            return True

        return any(trigger in answer_lower for trigger in FALLBACK_TRIGGERS)

    # ── PUBLIC: main entry point ───────────────────────────────────────────────
    def answer_with_fallback(
        self,
        query: str,
        local_answer: str,
        generic_name: str | None = None,
    ) -> FallbackResult:
        """
        If local answer is good → return it unchanged.
        If local answer signals missing info → search the web.

        Parameters
        ----------
        query        : original user question
        local_answer : answer generated from local ChromaDB chunks
        generic_name : resolved generic drug name (helps focus web search)

        Returns
        -------
        FallbackResult — always has a valid answer string.
        """
        if not self.needs_fallback(local_answer):
            return FallbackResult(
                answer=local_answer,
                used_fallback=False,
                source="local",
                source_url=None,
            )

        return self._search_and_answer(query, generic_name)

    # ── PRIVATE: web search ────────────────────────────────────────────────────
    def _search_and_answer(
        self,
        query: str,
        generic_name: str | None = None,
    ) -> FallbackResult:
        """
        Call OpenAI responses.create with web_search_preview tool.
        This is the correct API for openai >= 1.66.0 / 2.x.
        """
        search_input = self._build_search_input(query, generic_name)

        try:
            response = self.client.responses.create(
                model=self.model,
                tools=[{"type": "web_search_preview"}],
                input=[
                    {
                        "role": "system",
                        "content": _WEB_SEARCH_SYSTEM,
                    },
                    {
                        "role": "user",
                        "content": search_input,
                    }
                ],
            )

            answer    = self._extract_text(response)
            source_url = self._extract_url(response)

            if not answer or len(answer.strip()) < 20:
                return FallbackResult(
                    answer="This information could not be found in trusted medical sources.",
                    used_fallback=True,
                    source="web_empty",
                    source_url=None,
                )

            return FallbackResult(
                answer=answer.strip(),
                used_fallback=True,
                source="web",
                source_url=source_url,
            )

        except Exception as e:
            print(f"[web_fallback] ERROR: {type(e).__name__}: {e}")
            return FallbackResult(
                answer="This information could not be found in trusted medical sources.",
                used_fallback=True,
                source="error",
                source_url=None,
            )

    # ── PRIVATE: helpers ───────────────────────────────────────────────────────
    def _build_search_input(self, query: str, generic_name: str | None) -> str:
        """Build a focused medical search query for the web search tool."""
        if generic_name:
            return (
                f"Find information about {generic_name} for this question: {query}\n"
                f"Search trusted medical sources: fda.gov, medlineplus.gov, nih.gov"
            )
        return (
            f"Find information for this medical question: {query}\n"
            f"Search trusted medical sources: fda.gov, medlineplus.gov, nih.gov"
        )

    def _extract_text(self, response) -> str:
        """Extract text content from responses.create output."""
        try:
            for item in response.output:
                # message type items have content blocks
                if hasattr(item, "type") and item.type == "message":
                    if hasattr(item, "content"):
                        for block in item.content:
                            if hasattr(block, "type") and block.type == "output_text":
                                return block.text
                            if hasattr(block, "text"):
                                return block.text
                # direct text attribute
                if hasattr(item, "text") and item.text:
                    return item.text
        except Exception as e:
            print(f"[web_fallback] text extraction error: {e}")
        return ""

    def _extract_url(self, response) -> str | None:
        """Extract the first cited URL from web search annotations."""
        try:
            for item in response.output:
                if hasattr(item, "content"):
                    for block in item.content:
                        if hasattr(block, "annotations"):
                            for ann in block.annotations:
                                if hasattr(ann, "url") and ann.url:
                                    return ann.url
                        if hasattr(block, "url") and block.url:
                            return block.url
        except Exception:
            pass
        return None