import json
import logging
import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# =====================
# CLEANING PROMPT
# =====================
CLEAN_PROMPT = """You are cleaning raw text extracted from PDFs for a retrieval system.

Your job is ONLY to fix formatting issues while preserving the exact original wording.

=====================
STRICT RULES
=====================

- DO NOT summarize
- DO NOT rephrase
- DO NOT change wording
- DO NOT remove meaningful content
- DO NOT add new content
- DO NOT interpret or infer missing context
- Treat the input as an isolated chunk (it may start/end mid-sentence)

=====================
CLEANING RULES
=====================

You MUST:

1. Remove formatting noise ONLY when clearly non-semantic:
   - leading dots or repeated punctuation (e.g., ". ", "...", "•")
   - stray symbols (e.g., "|", extra hyphens)
   - duplicated spaces

2. Fix spacing:
   - normalize multiple spaces → single space

3. Fix line breaks:
   - join lines that are clearly part of the same sentence
   - keep paragraph breaks if they indicate structure
   - do NOT merge unrelated lines

4. Preserve structure:
   - keep headings, lists, and organization names exactly as written
   - keep capitalization unchanged

IMPORTANT:
- If unsure whether something is noise, KEEP IT

=====================
TEXT
=====================

{content}

=====================
RETURN CLEANED TEXT ONLY
=====================
"""

# TITLE PROMPT

TITLE_PROMPT = """You are a medical knowledge assistant optimizing content for semantic search retrieval.

Text:
{content}

Instructions:
- Title MUST be under 10 words
- Make it specific and search-friendly
- Avoid generic titles like "Overview" or "Advancements"

Return ONLY the title text. No JSON.
"""

# CLEANING FUNCTION

def clean_one(chunk):
    content = chunk.get("content", "").strip()

    if not content:
        return chunk

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": CLEAN_PROMPT.format(content=content[:1200])}
            ],
            temperature=0.0,
        )

        cleaned = response.choices[0].message.content.strip()

        # small extra safety cleanup
        cleaned = cleaned.lstrip(". ").strip()

        return {
            **chunk,
            "content": cleaned
        }

    except Exception as e:
        logger.warning("Cleaning failed for chunk '%s...': %s", content[:60], e)
        return chunk


def clean_chunks(chunks, batch_size=20):
    cleaned = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]

        logger.info(
            "Cleaning chunks %d–%d of %d",
            i + 1,
            min(i + batch_size, len(chunks)),
            len(chunks),
        )

        results = [clean_one(c) for c in batch]
        cleaned.extend(results)

    return cleaned


# TITLE FUNCTION
def title_one(chunk):
    content = chunk.get("content", "").strip()

    # skip bad chunks
    if len(content.split()) < 80 or "references" in content.lower():
        return {**chunk, "title": ""}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": TITLE_PROMPT.format(content=content[:1200])}
            ],
            temperature=0.2,
        )

        title = response.choices[0].message.content.strip()

        # safety checks
        if not title or len(title.split()) > 12:
            return {**chunk, "title": ""}

        return {
            **chunk,
            "title": title
        }

    except Exception as e:
        logger.warning("Title generation failed for '%s...': %s", content[:60], e)
        return {**chunk, "title": ""}


def generate_titles(chunks, batch_size=20):
    enriched = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]

        logger.info(
            "Generating titles %d–%d of %d",
            i + 1,
            min(i + batch_size, len(chunks)),
            len(chunks),
        )

        results = [title_one(c) for c in batch]
        enriched.extend(results)

    failed = sum(1 for c in enriched if not c.get("title"))
    if failed:
        logger.warning("%d/%d chunks missing titles.", failed, len(chunks))

    return enriched


# FULL PIPELINE
def process_chunks(chunks):
    logger.info("Starting cleaning step...")
    cleaned = clean_chunks(chunks)

    logger.info("Starting title generation step...")
    enriched = generate_titles(cleaned)

    return enriched
