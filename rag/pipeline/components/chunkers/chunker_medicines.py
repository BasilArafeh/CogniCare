"""
Groups medicine JSON fields by the question they answer — for example, warnings, side_effects, and precautions all go into one chunk because they all answer "what are the symptoms/side effects?". This way when a patient asks about side effects, ChromaDB retrieves exactly that chunk and nothing else.
Token limits (min 100, max 512) are enforced to keep chunk quality consistent — chunks that are too small get merged with their neighbors so they don't lose context, and chunks that are too long get split with a 100-token overlap so no information is cut off at the boundary.
Every chunk starts with the medicine name and brand names as a header, and carries metadata (generic name, brand names, chunk type, source) so ChromaDB can filter by medicine or question type before doing vector search.
"""

import json
import os
import tiktoken
from tqdm import tqdm

# ── Paths ───────────────────────────────────────────────────────
RAW_DIR       = "./data/raw/medication_files"
PROCESSED_DIR = "./data/processed/medication_files"
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ── Config ──────────────────────────────────────────────────────
MIN_TOKENS     = 100
MAX_TOKENS     = 512
OVERLAP_TOKENS = 100

# ── Token counter ────────────────────────────────────────────────
encoder = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    return len(encoder.encode(text))

# ── Field groups (by meaning) ────────────────────────────────────
FIELD_GROUPS = [
    {
        "name":    "identity_and_usage",
        "fields":  ["brand_names", "drug_class", "indications", "description"],
        "purpose": "What is this medicine and what is it used for?"
    },
    {
        "name":    "side_effects_and_warnings",
        "fields":  ["side_effects", "warnings", "precautions"],
        "purpose": "What are the side effects, symptoms, and warnings?"
    },
    {
        "name":    "dosage",
        "fields":  ["dosage"],
        "purpose": "How much should be taken and how often?"
    },
    {
        "name":    "interactions_and_overdose",
        "fields":  ["drug_interactions", "overdose", "contraindications"],
        "purpose": "What drugs interact with this? What happens on overdose?"
    },
    {
        "name":    "storage",
        "fields":  ["storage"],
        "purpose": "How should this medicine be stored?"
    },
]

# ── Helpers ──────────────────────────────────────────────────────
def extract_field_text(drug, fields):
    parts = []
    for field in fields:
        val = drug.get(field, "")
        if isinstance(val, list):
            val = ", ".join(val)
        if val and val.strip():
            label = field.replace("_", " ").title()
            parts.append(f"{label}: {val.strip()}")
    return "\n".join(parts)


def build_header(drug):
    generic = drug.get("generic_name", "").title()
    brands  = ", ".join(drug.get("brand_names", []))
    return f"Medicine: {generic} (also known as: {brands})\n"


def build_metadata(drug, chunk_name, tokens, part=None):
    return {
        "generic_name": drug.get("generic_name", "").lower(),
        "brand_names":  ", ".join(drug.get("brand_names", [])).lower(),
        "manufacturer": drug.get("manufacturer", "Unknown"),
        "drug_class":   ", ".join(drug.get("drug_class", [])),
        "chunk_type":   chunk_name,
        "chunk_part":   part if part else 1,
        "token_count":  tokens,
        "source":       "openFDA",
    }


def split_long_text(header, text, max_tokens, overlap_tokens):
    words = text.split()
    chunks, current_words = [], []
    current_tokens = count_tokens(header)

    for word in words:
        wt = count_tokens(word + " ")
        if current_tokens + wt > max_tokens:
            chunks.append(header + " ".join(current_words))
            overlap_words, overlap_count = [], 0
            for w in reversed(current_words):
                wt2 = count_tokens(w + " ")
                if overlap_count + wt2 > overlap_tokens:
                    break
                overlap_words.insert(0, w)
                overlap_count += wt2
            current_words = overlap_words + [word]
            current_tokens = count_tokens(header) + overlap_count + wt
        else:
            current_words.append(word)
            current_tokens += wt

    if current_words:
        chunks.append(header + " ".join(current_words))

    return chunks


# ── Main chunker ─────────────────────────────────────────────────
def chunk_medicine(drug):
    header, chunks, pending = build_header(drug), [], ""
    pending_fields = []

    for group in FIELD_GROUPS:
        text = extract_field_text(drug, group["fields"])
        if not text.strip():
            continue

        # Clean duplicate labels e.g. "Warnings: Warnings..."
        for label in ["Warnings", "Side Effects", "Dosage", "Storage"]:
            text = text.replace(f"{label}: {label}", f"{label}:")

        combined = header + text
        tokens   = count_tokens(combined)

        if tokens < MIN_TOKENS:
            pending += ("\n\n" + text if pending else text)
            pending_fields.append(group["name"])

        elif tokens > MAX_TOKENS:
            if pending:
                merged_text   = header + pending
                merged_tokens = count_tokens(merged_text)
                chunks.append({
                    "chunk_id": f"{drug['generic_name']}_merged_{len(chunks)+1}",
                    "text":     merged_text,
                    "metadata": build_metadata(drug, "merged_" + "_".join(pending_fields), merged_tokens),
                })
                pending, pending_fields = "", []

            sub_chunks = split_long_text(header, text, MAX_TOKENS, OVERLAP_TOKENS)
            for i, sub in enumerate(sub_chunks):
                sub_tokens = count_tokens(sub)
                chunks.append({
                    "chunk_id": f"{drug['generic_name']}_{group['name']}_part{i+1}",
                    "text":     sub,
                    "metadata": build_metadata(drug, group["name"], sub_tokens, part=i+1),
                })

        else:
            if pending:
                pt = count_tokens(header + pending)
                if pt >= MIN_TOKENS:
                    chunks.append({
                        "chunk_id": f"{drug['generic_name']}_merged_{len(chunks)+1}",
                        "text":     header + pending,
                        "metadata": build_metadata(drug, "merged_" + "_".join(pending_fields), pt),
                    })
                    pending, pending_fields = "", []
                else:
                    text    = pending + "\n\n" + text
                    pending, pending_fields = "", []

            final_text   = header + text
            final_tokens = count_tokens(final_text)
            chunks.append({
                "chunk_id": f"{drug['generic_name']}_{group['name']}",
                "text":     final_text,
                "metadata": build_metadata(drug, group["name"], final_tokens),
            })

    if pending:
        merged_text   = header + pending
        merged_tokens = count_tokens(merged_text)
        chunks.append({
            "chunk_id": f"{drug['generic_name']}_merged_{len(chunks)+1}",
            "text":     merged_text,
            "metadata": build_metadata(drug, "merged_" + "_".join(pending_fields), merged_tokens),
        })

    return chunks


# ── Save chunks to processed folder ─────────────────────────────
def save_chunks(generic_name, chunks):
    """
    Saves all chunks for one medicine as a single JSON file
    in rag/data/processed/medication_files/
    Example: acetaminophen_chunks.json
    """
    filename = generic_name.replace(" ", "_") + "_chunks.json"
    filepath = os.path.join(PROCESSED_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)


# ── Process all medicine JSON files ──────────────────────────────
def chunk_all_medicines():
    files = [f for f in os.listdir(RAW_DIR) if f.endswith(".json")]

    if not files:
        print(f"No JSON files found in {RAW_DIR}")
        return

    print(f"Found {len(files)} medicine files\n")

    total_chunks = 0
    skipped      = 0

    for filename in tqdm(files, desc="Chunking"):
        filepath = os.path.join(RAW_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            drug = json.load(f)

        # Skip files where FDA had no data
        if drug.get("fda_found") == False:
            skipped += 1
            continue

        chunks = chunk_medicine(drug)
        save_chunks(drug.get("generic_name", filename), chunks)
        total_chunks += len(chunks)

    print(f"\n✅ Done!")
    print(f"   Medicines chunked : {len(files) - skipped}")
    print(f"   Skipped (no FDA)  : {skipped}")
    print(f"   Total chunks saved: {total_chunks}")
    print(f"   Saved to          : {PROCESSED_DIR}")


if __name__ == "__main__":
    chunk_all_medicines()