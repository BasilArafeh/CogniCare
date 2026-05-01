ENRICH_PROMPT = """You are processing a medical text chunk for a retrieval system.

Return your response in EXACTLY this format:
TITLE: [under 10 words, specific and search-friendly — avoid "Overview" or "Advancements"]
TEXT: [cleaned text here]

Cleaning rules for TEXT:
- Preserve exact wording — do NOT summarize, rephrase, or change meaning
- Treat the input as an isolated chunk (it may start/end mid-sentence)
- Remove formatting noise: leading dots/bullets, stray symbols (|, extra hyphens), duplicate spaces
- Fix line breaks: join lines that are part of the same sentence; keep paragraph breaks
- Preserve headings, lists, and capitalization exactly as written
- When unsure whether something is noise, KEEP IT

{content}"""
