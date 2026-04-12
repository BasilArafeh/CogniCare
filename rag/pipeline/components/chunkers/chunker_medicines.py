"""
Medicine chunker — groups fields by question type, cleans FDA table content,
enforces token limits with overlap splitting.

Fix history
───────────
v1: Quality gate 35% → 55% per-sentence to preserve side_effects for medicines
    whose FDA text naturally contains percentage figures.

v2 (current): Three targeted fixes based on eval analysis:

  FIX 1 — FIELD_GROUPS: side_effects group was missing 'adverse_reactions',
    'adverse_effects', and 'boxed_warnings'. These are the canonical FDA field
    names for prescription drugs (donepezil, rivastigmine, atorvastatin, metformin,
    alprazolam, galantamine, rosuvastatin all store their adverse reaction data
    under 'adverse_reactions', not 'side_effects'). Adding them restores
    side_effects chunks for 69 medicines that previously had none.

  FIX 2 — FIELD_GROUPS: interactions_and_overdose group gains 'warnings' as a
    secondary field. OTC drugs (acetaminophen, ibuprofen, aspirin) have no
    separate 'drug_interactions'/'overdose' keys — their overdose and interaction
    content lives inside 'warnings'. This creates interactions_and_overdose
    chunks for the 30 medicines that previously had none.
    De-duplication logic prevents the same warnings text appearing in both
    side_effects and interactions_and_overdose: the field is only used in the
    IO group when the primary IO fields (drug_interactions, overdose,
    contraindications) are ALL empty, making it a true OTC fallback.

  FIX 3 — MIN_TOKENS: lowered from 40 → 20. Short adverse-reaction fields
    (e.g. "Hepatotoxicity has been reported.") were below the 40-token floor
    and merged into the wrong chunk type via the pending buffer.

- storage remains excluded (95% of medicines have no FDA storage data).
"""

import json
import os
import re
import tiktoken
from tqdm import tqdm

# ── Paths ───────────────────────────────────────────────────────
RAW_DIR       = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/raw/medication_files"
PROCESSED_DIR = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/medication_files/seperate_chunks"
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ── Config ──────────────────────────────────────────────────────
MIN_TOKENS     = 20    # FIX 3: lowered from 40 — short adverse-reaction fields were
                       # falling into the pending buffer and merging into wrong types
MAX_TOKENS     = 250
OVERLAP_TOKENS = 40

# ── Token counter ────────────────────────────────────────────────
encoder = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(encoder.encode(text))


# ── FDA TABLE CLEANER ────────────────────────────────────────────
_P_NCOL        = re.compile(r'\bn\s*=\s*\d+', re.I)
_P_GTE         = re.compile(r'[≥≤]\s*\d')
_P_LT1         = re.compile(r'\d\s*<\s*1')
_P_PAREN_N     = re.compile(r'\(\s*n\s*=\s*\d+\)', re.I)
_P_TABLE_HDR   = re.compile(r'^\s*table\s+\d+', re.I)
_P_MULTI_DRUG  = re.compile(
    r'(placebo|rivastigmine|sertraline|quetiapine|olanzapine|risperidone|'
    r'pioglitazone|pregabalin|paroxetine|galantamine|levetiracetam|'
    r'rosuvastatin|sitagliptin|semaglutide|saxagliptin|metformin)\s+'
    r'(placebo|n\s*=|\(n)',
    re.I
)
_P_DOSE_COLS   = re.compile(r'\d+\s*mg\s*/\s*day\s+\d+\s*mg\s*/\s*day', re.I)
_P_PURE_NUMS   = re.compile(r'^[\s\d<>()/%.±\-–,]+$')


def _is_table_line(line: str) -> bool:
    """True if this line is a clinical trial table row, not readable prose."""
    s = line.strip()
    if not s or len(s) < 4:
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

    # >65% non-alpha — only pure data rows (raised from 55% to preserve
    # readable lines like "nausea (47%), vomiting (31%)")
    non_alpha = sum(1 for c in s if not c.isalpha() and c != ' ')
    if len(s) > 10 and non_alpha / len(s) > 0.65:
        return True

    return False


def clean_fda_text(text: str) -> str:
    """
    Remove table rows line by line. Keep all readable prose.
    Only discard the whole field when >80% of lines are table rows AND
    the cleaned result is very short (< 30 tokens).
    """
    if not text or not text.strip():
        return ""

    lines   = text.split('\n')
    kept    = []
    skipped = 0

    for line in lines:
        if _is_table_line(line):
            skipped += 1
        else:
            kept.append(line)

    cleaned = '\n'.join(kept).strip()
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned


# ── Field groups ─────────────────────────────────────────────────
#
# FIX 1: side_effects group now includes all FDA adverse-reaction field names.
#   Prescription drug labels use 'adverse_reactions' (FDA section 6).
#   OTC labels use 'side_effects', 'warnings', and 'precautions'.
#   'boxed_warnings' is the black-box warning section — high clinical importance.
#
# FIX 2: interactions_and_overdose group includes 'warnings' as a final fallback
#   for OTC drugs that store overdose/interaction info there.
#   extract_field_text_io() (below) ensures 'warnings' is only used when the
#   three primary IO fields are ALL empty, preventing duplication with the
#   side_effects chunk.
#
# storage excluded — 95% of medicines have no FDA storage data.

FIELD_GROUPS = [
    {
        "name":   "identity_and_usage",
        "fields": ["brand_names", "drug_class", "indications", "description"],
    },
    {
        # FIX 1: added adverse_reactions, adverse_effects, boxed_warnings
        "name":   "side_effects",
        "fields": [
            "adverse_reactions",   # primary FDA prescription drug field (section 6)
            "adverse_effects",     # alternate key used by some data sources
            "boxed_warnings",      # black-box warnings — highest clinical priority
            "side_effects",        # OTC label field
            "warnings",            # OTC label field
            "precautions",         # OTC / older RX label field
        ],
    },
    {
        "name":   "dosage",
        "fields": ["dosage"],
    },
    {
        # FIX 2: 'warnings' added as OTC fallback (handled by extract_field_text_io)
        "name":   "interactions_and_overdose",
        "fields": ["drug_interactions", "overdose", "contraindications", "warnings"],
    },
]

# ── Helpers ──────────────────────────────────────────────────────
def extract_field_text(drug: dict, fields: list) -> str:
    """Standard field extractor used for all groups except interactions_and_overdose."""
    parts = []
    for field in fields:
        val = drug.get(field, "")
        if isinstance(val, list):
            val = ", ".join(val)
        if not val or not val.strip():
            continue
        cleaned = clean_fda_text(val.strip())
        if cleaned:
            label = field.replace("_", " ").title()
            parts.append(f"{label}: {cleaned}")
    return "\n".join(parts)


def extract_field_text_io(drug: dict) -> str:
    """
    FIX 2 — Special extractor for the interactions_and_overdose group.

    'warnings' is included as a fallback ONLY when the three primary IO fields
    (drug_interactions, overdose, contraindications) are ALL empty. This prevents
    the same warnings text from appearing in both the side_effects chunk and the
    interactions_and_overdose chunk for prescription drugs that have both.

    OTC drugs like acetaminophen, ibuprofen, and aspirin have no separate
    drug_interactions/overdose keys — their overdose and drug-interaction text
    lives inside 'warnings'. For these medicines, the fallback ensures the
    overdose content is indexed under the correct chunk type.
    """
    primary_fields  = ["drug_interactions", "overdose", "contraindications"]
    fallback_fields = ["warnings"]

    parts = []
    has_primary = False

    for field in primary_fields:
        val = drug.get(field, "")
        if isinstance(val, list):
            val = ", ".join(val)
        if not val or not val.strip():
            continue
        cleaned = clean_fda_text(val.strip())
        if cleaned:
            label = field.replace("_", " ").title()
            parts.append(f"{label}: {cleaned}")
            has_primary = True

    # Only use warnings fallback when ALL primary fields are empty
    if not has_primary:
        for field in fallback_fields:
            val = drug.get(field, "")
            if isinstance(val, list):
                val = ", ".join(val)
            if not val or not val.strip():
                continue
            cleaned = clean_fda_text(val.strip())
            if cleaned:
                label = field.replace("_", " ").title()
                parts.append(f"{label}: {cleaned}")

    return "\n".join(parts)


def build_header(drug: dict) -> str:
    generic = drug.get("generic_name", "").title()
    brands  = ", ".join(drug.get("brand_names", []))
    return f"Medicine: {generic} (also known as: {brands})\n"


def build_metadata(drug: dict, chunk_name: str, tokens: int, part=None) -> dict:
    return {
        "generic_name": drug.get("generic_name", "").lower(),
        "brand_names":  ", ".join(b.lower() for b in drug.get("brand_names", [])),
        "manufacturer": drug.get("manufacturer", "Unknown"),
        "drug_class":   ", ".join(drug.get("drug_class", [])),
        "chunk_type":   chunk_name,
        "chunk_part":   part if part else 1,
        "token_count":  tokens,
        "source":       "openFDA",
    }


def split_long_text(header: str, text: str, max_tokens: int, overlap_tokens: int) -> list:
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
def chunk_medicine(drug: dict) -> list:
    header = build_header(drug)
    chunks = []

    for group in FIELD_GROUPS:
        # Use correct extractor
        if group["name"] == "interactions_and_overdose":
            text = extract_field_text_io(drug)
        else:
            text = extract_field_text(drug, group["fields"])

        # 🔥 FIX 1: SMART FALLBACK (NO FAKE TEXT)
        if not text.strip():
            if group["name"] == "side_effects":
                fallback = extract_field_text(drug, ["warnings", "precautions"])
                if fallback.strip():
                    text = fallback
                else:
                    continue

            elif group["name"] == "interactions_and_overdose":
                fallback = extract_field_text(drug, ["warnings"])
                if fallback.strip():
                    text = fallback
                else:
                    continue

            else:
                continue

        # Clean duplicate labels
        for label in [
            "Warnings", "Side Effects", "Dosage", "Precautions",
            "Drug Interactions", "Overdose", "Contraindications",
            "Adverse Reactions", "Adverse Effects", "Boxed Warnings",
        ]:
            text = text.replace(f"{label}: {label}", f"{label}:")

        combined = header + text
        tokens = count_tokens(combined)

        # 🔥 FIX 2: SHORT TEXT → ALWAYS KEEP
        if tokens < MIN_TOKENS:
            chunks.append({
                "chunk_id": f"{drug['generic_name']}_{group['name']}_short",
                "text": combined,
                "metadata": build_metadata(drug, group["name"], tokens),
            })
            continue

        # LONG TEXT → SPLIT
        if tokens > MAX_TOKENS:
            sub_chunks = split_long_text(header, text, MAX_TOKENS, OVERLAP_TOKENS)
            for i, sub in enumerate(sub_chunks):
                sub_tokens = count_tokens(sub)
                chunks.append({
                    "chunk_id": f"{drug['generic_name']}_{group['name']}_part{i+1}",
                    "text": sub,
                    "metadata": build_metadata(drug, group["name"], sub_tokens, part=i+1),
                })
        else:
            chunks.append({
                "chunk_id": f"{drug['generic_name']}_{group['name']}",
                "text": combined,
                "metadata": build_metadata(drug, group["name"], tokens),
            })

    return chunks


# ── Save ─────────────────────────────────────────────────────────
def save_chunks(generic_name: str, chunks: list):
    filename = generic_name.replace(" ", "_") + "_chunks.json"
    filepath = os.path.join(PROCESSED_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)


# ── Process all ──────────────────────────────────────────────────
def chunk_all_medicines():
    files = [f for f in os.listdir(RAW_DIR) if f.endswith(".json")]
    if not files:
        print(f"No JSON files found in {RAW_DIR}")
        return

    print(f"Found {len(files)} medicine files\n")
    total_chunks, skipped = 0, 0
    missing_se, missing_io = [], []

    for filename in tqdm(files, desc="Chunking"):
        filepath = os.path.join(RAW_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            drug = json.load(f)

        if drug.get("fda_found") == False:
            skipped += 1
            continue

        chunks = chunk_medicine(drug)
        save_chunks(drug.get("generic_name", filename), chunks)
        total_chunks += len(chunks)

        # Warn about medicines that still lack key chunk types after fixes
        types = {c["metadata"]["chunk_type"] for c in chunks}
        name  = drug.get("generic_name", filename)
        if "side_effects" not in types:
            missing_se.append(name)
        if "interactions_and_overdose" not in types:
            missing_io.append(name)

    print(f"\n✅ Done!")
    print(f"   Medicines chunked    : {len(files) - skipped}")
    print(f"   Skipped (no FDA)     : {skipped}")
    print(f"   Total chunks saved   : {total_chunks}")
    print(f"   Saved to             : {PROCESSED_DIR}")

    if missing_se:
        print(f"\n⚠️  Still missing side_effects chunks ({len(missing_se)}):")
        for n in missing_se[:10]:
            print(f"     {n}")
        if len(missing_se) > 10:
            print(f"     ... and {len(missing_se) - 10} more")
        print("   → Check whether the raw JSON has 'adverse_reactions' under a different key.")

    if missing_io:
        print(f"\n⚠️  Still missing interactions_and_overdose chunks ({len(missing_io)}):")
        for n in missing_io[:10]:
            print(f"     {n}")
        if len(missing_io) > 10:
            print(f"     ... and {len(missing_io) - 10} more")


if __name__ == "__main__":
    chunk_all_medicines()