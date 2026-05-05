from __future__ import annotations

from rag.retrieval.retriever import RetrievedChunk

SYSTEM_PROMPT = """You are a caregiver support assistant for families caring for people with Alzheimer's disease and related dementias.

How to use the context:
- Treat the provided context excerpts as your primary evidence. Give a helpful, concrete answer whenever those excerpts reasonably address the caregiver's question — including by summarizing, paraphrasing, or weaving together facts that clearly appear across one or more excerpts.
- It is okay if the excerpts use different wording than the question; match ideas and substance, not exact phrases.
- If the excerpts are only partly relevant, share what they support in plain language, then briefly note what they do not cover (without inventing specifics). Do not withhold the partial answer.

When to refuse briefly:
- Reply exactly: \"I don't have enough information.\" ONLY when none of the excerpts meaningfully relates to what the caregiver is asking (for example unrelated topics, or snippets with no plausible link to dementia or caregiving). Mild gaps or imperfect alignment are normal — answer from what fits instead of refusing.

Safety and grounding:
- Do not invent facts, symptoms, diagnoses, timelines, medications, dosages, or clinical advice beyond what those excerpts reasonably support.
- Never recommend changing, stopping, starting, splitting, doubling, skipping, or altering any medication dose — always direct the caregiver to a pharmacist or clinician for dosing and medication decisions.
- Use a calm, clear, jargon-light tone tailored to caregivers who may be exhausted or distressed.

Emergency handling:
If the caregiver's query mentions any of these ideas (even roughly): overdose, severe reaction, fall, unconscious, or emergency — you MUST start your reply with a single line exactly in this form (fill in <reason> with a brief cause tied to the query):
ESCALATE: <reason>

Then skip a blank line before the rest of your answer. Outside of that line you still follow every rule above."""

EMERGENCY_KEYWORDS = frozenset(
    ("overdose", "severe reaction", "fall", "unconscious", "emergency")
)


def _query_suggests_emergency(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in EMERGENCY_KEYWORDS)


def _brand_names_display(metadata: dict) -> str:
    names = metadata.get("brand_names")
    if isinstance(names, list) and names:
        return ", ".join(str(x) for x in names if x)
    return "unknown"


def _format_chunk_block(chunk: RetrievedChunk) -> str:
    meta = chunk.metadata
    if chunk.source == "medical":
        label = (
            f"[Source: {meta.get('source_folder')} | "
            f"{meta.get('filename')} | Section: {meta.get('section_title')}]"
        )
    else:
        generic = meta.get("generic_name")
        gn = generic if generic else "unknown"
        brands = _brand_names_display(meta)
        chunk_type = meta.get("chunk_type", "unknown")
        label = f"[Drug: {gn} ({brands}) | Type: {chunk_type}]"

    body = chunk.text.strip()
    return f"{label}\n{body}"


def build_prompt(query: str, chunks: list[RetrievedChunk]) -> list[dict]:
    """Build OpenAI chat messages: system constraints + contextual user payload."""

    escalation_note = ""
    if _query_suggests_emergency(query):
        escalation_note = (
            "\n\nNote: This query mentions an emergency-related concern — "
            "you must emit the ESCALATE line described above."
        )

    blocks = [_format_chunk_block(c) for c in chunks]
    context_body = (
        "\n\n---\n\n".join(blocks)
        if blocks
        else "(No context snippets were retrieved — if asked for specifics, reply that you lack information.)"
    )

    user_content = (
        "Use only the context excerpts below plus this question.\n\n"
        "--- Context excerpts ---\n\n"
        f"{context_body}\n\n"
        "--- Caregiver question ---\n"
        f"{query.strip()}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT + escalation_note},
        {"role": "user", "content": user_content},
    ]
