import os
import sys
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from documents.extract import extract_pdf_elements
from documents.clean import clean_elements
from documents.chunk import chunk_elements
from documents.enrich import process_chunks as llm_enrich_chunks

DATA_FOLDERS = [
    "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/raw/communication_guidelines",
    "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/raw/mental_health",
    "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/raw/alzheimers_and_other_sicknesses"
]

OUTPUT_PATH = "/Users/leensalman/Desktop/gp2/rag/data/processed/chunks.json"

def is_good_chunk(content):
    text = content.lower()

    if "references" in text:
        return False

    if text.startswith("."):
        return False

    if text.count(".") > 20:
        return False

    if len(text.split()) < 50:
        return False

    return True

def process_pdf(file_path: str, category: str, debug: bool = False):
    print(f"\nProcessing: {file_path}")

    # 1. Extract
    elements = extract_pdf_elements(file_path)

    # 2. Clean
    cleaned = clean_elements(elements)

    # 3. Chunk
    chunks = chunk_elements(cleaned)
    chunks = [c for c in chunks if is_good_chunk(c["content"])]

    # 4. Enrich
    enriched = llm_enrich_chunks(chunks)

    # 5. Metadata
    final_chunks = add_metadata(
        enriched,
        source_file=file_path,
        category=category
    )

    if debug:
        print(f"Chunks created: {len(final_chunks)}")

    return final_chunks


# PROCESS ALL FOLDERS

def process_all_folders(debug: bool = False):
    all_chunks = []

    for folder in DATA_FOLDERS:
        category = os.path.basename(folder)

        print(f"\n📁 Processing category: {category}")

        for file in os.listdir(folder):
            if not file.endswith(".pdf"):
                continue

            file_path = os.path.join(folder, file)

            try:
                chunks = process_pdf(file_path, category, debug)
                all_chunks.extend(chunks)

            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")

    print(f"\n✅ Total chunks created: {len(all_chunks)}")
    return all_chunks


# METADATA

def add_metadata(chunks, source_file, category):
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
            "id": str(uuid.uuid4()),

            # content
            "content": content,
            "embedding_text": embedding_text,

            # structure
            "title": title,
            "section": section,

            # metadata
            "category": category,
            "source": source_file,
            "file_name": file_name,
            "word_count": len(content.split()),
            "created_at": datetime.utcnow().isoformat(),

            # debug
            "full_text": f"""Title: {title}
Section: {section}

Content:
{content}
"""
        })

    return results


# SAVE

def save_chunks(chunks, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(chunks, f, indent=2)

    print(f"\n💾 Saved {len(chunks)} chunks to {output_path}")


# MAIN

if __name__ == "__main__":
    all_chunks = process_all_folders(debug=True)

    save_chunks(all_chunks, OUTPUT_PATH)