# test for the rag pipeline

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from documents.extract import extract_pdf_elements
from documents.clean import clean_elements
from documents.chunk import chunk_elements
from documents.enrich import process_chunks as llm_enrich_chunks


# =========================
# MAIN PIPELINE
# =========================

def process_pdf(file_path: str, debug: bool = False):
    # 1. Extract
    print("extracting...")
    elements = extract_pdf_elements(file_path)

    if debug:
        print(f"Extracted {len(elements)} elements")

    # 2. Clean
    print("cleaning...")
    cleaned = clean_elements(elements)

    if debug:
        print(f"Cleaned elements: {len(cleaned)}")

    # 3. Chunk
    print("chunking...")
    chunks = chunk_elements(cleaned)

    if debug:
        print(f"Generated chunks: {len(chunks)}")

    # 4. LLM enrichment
    print("generating titles...")
    enriched = llm_enrich_chunks(chunks)

    # 5. Add metadata
    print("adding metadata...")
    final_chunks = add_metadata(enriched, source_file=file_path)

    print(f"Done. Final chunks: {len(final_chunks)}")

    return final_chunks


# METADATA

def add_metadata(chunks, source_file):
    results = []
    file_name = os.path.basename(source_file).replace(".pdf", "")

    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "").strip()
        title = chunk.get("title", "").strip()
        section = chunk.get("section", "").strip()

        if not content:
            continue

        embedding_text = f"{title}\n\n{content}" if title else content

        results.append({
            "id": f"{file_name}_{i}",
            "section": section,
            "title": title,
            "content": content,
            "embedding_text": embedding_text,
            "word_count": len(content.split()),
            "source": source_file,

            # optional debug format
            "full_text": f"""Title: {title}
Section: {section}

Content:
{content}
"""
        })

    return results


# =========================
# DEBUG / PREVIEW
# =========================

def preview_chunks(chunks, n=5):
    print("\nPreviewing chunks...\n")

    for c in chunks[:n]:
        print("\n---")
        print("ID:", c["id"])
        print("SECTION:", c["section"])
        print("TITLE:", c["title"])
        print("CONTENT:", c["content"])


# =========================
# RUN PIPELINE
# =========================

if __name__ == "__main__":
    file_path = "/Users/leensalman/Desktop/gp2/rag/data/raw/alzheimers_and_other_sicknesses/alzheimers-facts-and-figures-special-report.pdf"

    chunks = process_pdf(file_path, debug=True)

    preview_chunks(chunks)