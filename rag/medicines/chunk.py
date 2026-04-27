"""
chunker_medicines.py  —  CogniCare Medicine Chunker (FIXED)
===========================================================

Fixes added:
1. Added administration chunk type
   - Helps patch/application/how-to-take questions.

2. Added special_populations chunk type
   - Helps elderly, dementia, Alzheimer’s, fall risk, sleep, and safety questions.

3. Added better labels for new chunk types
   - Improves embedding meaning for continuation chunks.

4. Added missing tracking for new chunk types
   - Prints warnings if administration/special_populations are missing.
"""

import json
import os
import re
import tiktoken
from tqdm import tqdm

# ── Paths ───────────────────────────────────────────────────────────────────────
RAW_DIR       = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/medicines/cleaned"
PROCESSED_DIR = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/medicines/chunks"
OUTPUT_DIR    = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/medicines"

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Config ──────────────────────────────────────────────────────────────────────
MIN_TOKENS     = 20
MAX_TOKENS     = 400
OVERLAP_TOKENS = 80

# ── Token counter ───────────────────────────────────────────────────────────────
encoder = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(encoder.encode(text))


# ── Sentence splitter ───────────────────────────────────────────────────────────
_SENT_RE = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z("])'
    r'|(?<=\.\d{1})\s+(?=[A-Z])'
)

def split_sentences(text: str) -> list[str]:
    parts = _SENT_RE.split(text)
    sentences = []
    for p in parts:
        p = p.strip()
        if p:
            sentences.append(p)
    return sentences if sentences else [text]


# ── FDA table cleaner ───────────────────────────────────────────────────────────
_P_NCOL       = re.compile(r'\bn\s*=\s*\d+', re.I)
_P_GTE        = re.compile(r'[≥≤]\s*\d')
_P_LT1        = re.compile(r'\d\s*<\s*1')
_P_PAREN_N    = re.compile(r'\(\s*n\s*=\s*\d+\)', re.I)
_P_TABLE_HDR  = re.compile(r'^\s*table\s+\d+', re.I)
_P_MULTI_DRUG = re.compile(
    r'(placebo|rivastigmine|sertraline|quetiapine|olanzapine|risperidone|'
    r'pioglitazone|pregabalin|paroxetine|galantamine|levetiracetam|'
    r'rosuvastatin|sitagliptin|semaglutide|saxagliptin|metformin)\s+'
    r'(placebo|n\s*=|\(n)',
    re.I
)
_P_DOSE_COLS  = re.compile(r'\d+\s*mg\s*/\s*day\s+\d+\s*mg\s*/\s*day', re.I)
_P_PURE_NUMS  = re.compile(r'^[\s\d<>()/%.±\-–,]+$')


def _is_table_line(line: str) -> bool:
    s = line.strip()

    if not s or len(s) < 4:
        return False

    if len(s) > 300:
        return False

    if _P_PURE_NUMS.match(s):
        return True

    hits = sum([
        bool(_P_NCOL.search(s)),
        bool(_P_GTE.search(s)),
        bool(_P_LT1.search(s)),
        bool(_P_PAREN_N.search(s)),
        bool(_P_TABLE_HDR.match(s)),
        bool(_P_MULTI_DRUG.search(s)),
        bool(_P_DOSE_COLS.search(s)),
    ])

    if hits >= 2:
        return True

    non_alpha = sum(1 for c in s if not c.isalpha() and c != ' ')
    if len(s) > 10 and non_alpha / len(s) > 0.65:
        return True

    return False


def clean_fda_text(text: str) -> str:
    if not text or not text.strip():
        return ""

    lines = text.split("\n")
    kept = [line for line in lines if not _is_table_line(line)]
    cleaned = "\n".join(kept).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned


# ── Field groups ────────────────────────────────────────────────────────────────
FIELD_GROUPS = [
    {
        "name": "identity_and_usage",
        "fields": ["brand_names", "drug_class", "indications", "description"],
    },
    {
        "name": "side_effects",
        "fields": [
            "adverse_reactions",
            "adverse_effects",
            "boxed_warnings",
            "side_effects",
            "warnings",
            "precautions",
        ],
    },
    {
        "name": "dosage",
        "fields": ["dosage"],
    },
    {
        "name": "administration",
        "fields": ["dosage", "storage"],
    },
    {
        "name": "special_populations",
        "fields": ["warnings", "precautions", "contraindications"],
    },
    {
        "name": "interactions_and_overdose",
        "fields": ["drug_interactions", "overdose", "contraindications", "warnings"],
    },
    {
        "name": "storage",
        "fields": ["storage"],
    },
]


# ── Field extractors ────────────────────────────────────────────────────────────
def extract_field_text(drug: dict, fields: list) -> str:
    parts = []

    for field in fields:
        val = drug.get(field, "")

        if isinstance(val, list):
            val = ", ".join(val)

        if not val or not str(val).strip():
            continue

        cleaned = clean_fda_text(str(val).strip())

        if cleaned:
            label = field.replace("_", " ").title()
            parts.append(f"{label}: {cleaned}")

    return "\n".join(parts)


def extract_field_text_io(drug: dict) -> str:
    """
    Special extractor for interactions_and_overdose.
    Warnings are used only when primary IO fields are empty.
    """
    primary_fields = ["drug_interactions", "overdose", "contraindications"]
    fallback_fields = ["warnings"]

    parts = []
    has_primary = False

    for field in primary_fields:
        val = drug.get(field, "")

        if isinstance(val, list):
            val = ", ".join(val)

        if not val or not str(val).strip():
            continue

        cleaned = clean_fda_text(str(val).strip())

        if cleaned:
            label = field.replace("_", " ").title()
            parts.append(f"{label}: {cleaned}")
            has_primary = True

    if not has_primary:
        for field in fallback_fields:
            val = drug.get(field, "")

            if isinstance(val, list):
                val = ", ".join(val)

            if not val or not str(val).strip():
                continue

            cleaned = clean_fda_text(str(val).strip())

            if cleaned:
                label = field.replace("_", " ").title()
                parts.append(f"{label}: {cleaned}")

    return "\n".join(parts)


# ── Header ──────────────────────────────────────────────────────────────────────
def build_header(drug: dict) -> str:
    generic = drug.get("generic_name", "").title()
    brands = ", ".join(b for b in drug.get("brand_names", []) if b)

    if brands:
        return f"Medicine: {generic} (also known as: {brands})\n"

    return f"Medicine: {generic}\n"


# ── Metadata ────────────────────────────────────────────────────────────────────
def build_metadata(
    drug: dict,
    chunk_name: str,
    tokens: int,
    part: int = 1,
    total_parts: int = 1,
) -> dict:
    return {
        "generic_name": drug.get("generic_name", "").lower(),
        "brand_names": ", ".join(b.lower() for b in drug.get("brand_names", [])),
        "manufacturer": drug.get("manufacturer", "Unknown"),
        "drug_class": ", ".join(drug.get("drug_class", [])),
        "chunk_type": chunk_name,
        "chunk_part": part,
        "total_parts": total_parts,
        "token_count": tokens,
        "source": "openFDA",
    }


# ── Section labels ──────────────────────────────────────────────────────────────
GROUP_LABELS = {
    "identity_and_usage": "Drug Identity and Usage",
    "side_effects": "Adverse Effects and Side Effects",
    "dosage": "Dosage and Administration",
    "administration": "Administration Instructions, Patch Use, How To Take",
    "special_populations": "Special Populations, Elderly Use, Dementia Safety",
    "interactions_and_overdose": "Drug Interactions, Overdose and Contraindications",
    "storage": "Storage and Handling",
}


# ── Sentence-aware splitter ─────────────────────────────────────────────────────
def split_long_text(
    header: str,
    text: str,
    max_tokens: int,
    overlap_tokens: int,
    section_label: str = "",
) -> list[str]:
    sentences = split_sentences(text)
    header_tokens = count_tokens(header)

    raw_chunks: list[list[str]] = []
    current: list[str] = []
    current_tokens = header_tokens

    for sent in sentences:
        st = count_tokens(sent + " ")

        # Single sentence longer than max: split by words as fallback
        if header_tokens + st > max_tokens and not current:
            words = sent.split()
            word_buf: list[str] = []
            word_tokens = header_tokens

            for word in words:
                wt = count_tokens(word + " ")

                if word_tokens + wt > max_tokens and word_buf:
                    raw_chunks.append(word_buf[:])
                    word_buf = [word]
                    word_tokens = header_tokens + wt
                else:
                    word_buf.append(word)
                    word_tokens += wt

            if word_buf:
                current = word_buf
                current_tokens = word_tokens

            continue

        if current_tokens + st > max_tokens and current:
            raw_chunks.append(current[:])

            overlap: list[str] = []
            overlap_t = 0

            for s in reversed(current):
                st2 = count_tokens(s + " ")

                if overlap_t + st2 > overlap_tokens:
                    break

                overlap.insert(0, s)
                overlap_t += st2

            current = overlap + [sent]
            current_tokens = header_tokens + overlap_t + st

        else:
            current.append(sent)
            current_tokens += st

    if current:
        raw_chunks.append(current)

    result = []

    for i, sentence_list in enumerate(raw_chunks):
        chunk_text = " ".join(sentence_list)

        if i == 0:
            result.append(header + chunk_text)
        else:
            prefix = f"[{section_label}] " if section_label else ""
            result.append(header + prefix + chunk_text)

    return result


# ── Main chunker ────────────────────────────────────────────────────────────────
def chunk_medicine(drug: dict) -> list:
    header = build_header(drug)
    chunks = []

    for group in FIELD_GROUPS:
        group_name = group["name"]

        if group_name == "interactions_and_overdose":
            text = extract_field_text_io(drug)
        else:
            text = extract_field_text(drug, group["fields"])

        # Smart fallbacks
        if not text.strip():
            if group_name == "side_effects":
                fallback = extract_field_text(drug, ["warnings", "precautions"])
                text = fallback if fallback.strip() else ""

            elif group_name == "interactions_and_overdose":
                fallback = extract_field_text(drug, ["warnings"])
                text = fallback if fallback.strip() else ""

            elif group_name == "special_populations":
                fallback = extract_field_text(drug, ["warnings", "precautions"])
                text = fallback if fallback.strip() else ""

            elif group_name == "administration":
                fallback = extract_field_text(drug, ["dosage"])
                text = fallback if fallback.strip() else ""

            if not text.strip():
                continue

        # Clean duplicate field label artifacts
        for label in [
            "Warnings",
            "Side Effects",
            "Dosage",
            "Precautions",
            "Drug Interactions",
            "Overdose",
            "Contraindications",
            "Adverse Reactions",
            "Adverse Effects",
            "Boxed Warnings",
            "Storage",
            "Administration",
        ]:
            text = text.replace(f"{label}: {label}", f"{label}:")

        combined = header + text
        tokens = count_tokens(combined)

        if tokens < MIN_TOKENS:
            chunks.append({
                "chunk_id": f"{drug['generic_name']}_{group_name}_short",
                "text": combined,
                "metadata": build_metadata(
                    drug,
                    group_name,
                    tokens,
                    part=1,
                    total_parts=1,
                ),
            })
            continue

        if tokens > MAX_TOKENS:
            section_label = GROUP_LABELS.get(group_name, "")

            sub_chunks = split_long_text(
                header,
                text,
                MAX_TOKENS,
                OVERLAP_TOKENS,
                section_label,
            )

            total = len(sub_chunks)

            for i, sub in enumerate(sub_chunks):
                sub_tokens = count_tokens(sub)

                chunks.append({
                    "chunk_id": f"{drug['generic_name']}_{group_name}_part{i + 1}",
                    "text": sub,
                    "metadata": build_metadata(
                        drug,
                        group_name,
                        sub_tokens,
                        part=i + 1,
                        total_parts=total,
                    ),
                })

        else:
            chunks.append({
                "chunk_id": f"{drug['generic_name']}_{group_name}",
                "text": combined,
                "metadata": build_metadata(
                    drug,
                    group_name,
                    tokens,
                    part=1,
                    total_parts=1,
                ),
            })

    return chunks


# ── Save ────────────────────────────────────────────────────────────────────────
def save_chunks(generic_name: str, chunks: list):
    filename = generic_name.replace(" ", "_") + "_chunks.json"
    filepath = os.path.join(PROCESSED_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)


# ── Process all ─────────────────────────────────────────────────────────────────
def chunk_all_medicines():
    files = [f for f in os.listdir(RAW_DIR) if f.endswith(".json")]

    if not files:
        print(f"No JSON files found in {RAW_DIR}")
        return

    print(f"Found {len(files)} medicine files\n")

    total_chunks = 0
    skipped = 0

    missing_se = []
    missing_io = []
    missing_admin = []
    missing_special = []

    for filename in tqdm(files, desc="Chunking"):
        filepath = os.path.join(RAW_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            drug = json.load(f)

        if drug.get("fda_found") is False:
            skipped += 1
            continue

        chunks = chunk_medicine(drug)
        save_chunks(drug.get("generic_name", filename), chunks)

        total_chunks += len(chunks)

        types = {c["metadata"]["chunk_type"] for c in chunks}
        name = drug.get("generic_name", filename)

        if "side_effects" not in types:
            missing_se.append(name)

        if "interactions_and_overdose" not in types:
            missing_io.append(name)

        if "administration" not in types:
            missing_admin.append(name)

        if "special_populations" not in types:
            missing_special.append(name)

    print("\n✅ Done!")
    print(f"   Medicines chunked  : {len(files) - skipped}")
    print(f"   Skipped (no FDA)   : {skipped}")
    print(f"   Total chunks saved : {total_chunks}")
    print(f"   Saved to           : {PROCESSED_DIR}")

    def print_missing(title: str, items: list[str]):
        if items:
            print(f"\n⚠️  Still missing {title} chunks ({len(items)}):")
            for n in items[:10]:
                print(f"     {n}")
            if len(items) > 10:
                print(f"     ... and {len(items) - 10} more")

    print_missing("side_effects", missing_se)
    print_missing("interactions_and_overdose", missing_io)
    print_missing("administration", missing_admin)
    print_missing("special_populations", missing_special)


# ── Merge all per-drug chunk files ──────────────────────────────────────────────
def merge_all_chunks():
    files = [f for f in os.listdir(PROCESSED_DIR) if f.endswith("_chunks.json")]

    if not files:
        print(f"No chunk files found in {PROCESSED_DIR}")
        return

    all_chunks = []

    for filename in files:
        filepath = os.path.join(PROCESSED_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        all_chunks.extend(chunks)

    master_path = os.path.join(OUTPUT_DIR, "all_medicine_chunks.json")

    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"✅ Merged {len(files)} files → {len(all_chunks)} total chunks")
    print(f"   Saved to: {master_path}")


if __name__ == "__main__":
    chunk_all_medicines()
    merge_all_chunks()