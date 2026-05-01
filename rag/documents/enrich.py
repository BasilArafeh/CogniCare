import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from dotenv import load_dotenv
from prompts.pdf_text_cleaner import ENRICH_PROMPT

load_dotenv()

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def enrich_one(chunk):
    content = chunk.get("content", "").strip()
    if not content:
        return {**chunk, "title": ""}

    skip_title = len(content.split()) < 80 or "references" in content.lower()

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": ENRICH_PROMPT.format(content=content[:1200])}
            ],
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()

        # Parse TITLE and TEXT sections
        title, cleaned = "", content
        if raw.startswith("TITLE:"):
            parts = raw.split("TEXT:", 1)
            title_part = parts[0].replace("TITLE:", "").strip()
            text_part  = parts[1].strip() if len(parts) > 1 else ""

            if not skip_title and title_part and len(title_part.split()) <= 12:
                title = title_part
            if text_part:
                cleaned = text_part.lstrip(". ").strip()

        return {**chunk, "content": cleaned, "title": title}

    except Exception as e:
        logger.warning("Enrichment failed for '%s...': %s", content[:60], e)
        return {**chunk, "title": ""}


def process_chunks(chunks, batch_size=20):
    enriched = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        logger.info(
            "Enriching chunks %d–%d of %d",
            i + 1, min(i + batch_size, len(chunks)), len(chunks),
        )
        enriched.extend(enrich_one(c) for c in batch)

    failed = sum(1 for c in enriched if not c.get("title"))
    if failed:
        logger.warning("%d/%d chunks missing titles.", failed, len(chunks))

    return enriched


if __name__ == "__main__":
    import sys
    from extract import extract_pdf_elements
    from clean import clean_elements
    from chunk import chunk_elements
    path = sys.argv[1] if len(sys.argv) > 1 else input("PDF path: ").strip()
    chunks = chunk_elements(clean_elements(extract_pdf_elements(path)))
    enriched = process_chunks(chunks)
    print(f"Enriched {len(enriched)} chunks")
    for c in enriched[:3]:
        print(f"\nTitle: {c.get('title', '(none)')}\n{c['content'][:200]}")
