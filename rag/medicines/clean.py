"""
clean_medication_jsons.py
Cleans raw openFDA medication JSON files for use in a RAG pipeline.

What it removes
───────────────
1. Leading section headers     — "1 INDICATIONS AND USAGE", "WARNINGS", "6.2 Clinical Trials..."
2. Inline subsection numbers   — the "6.1 " prefix in "6.1 Clinical Trials Experience Because..."
3. [see ...] cross-references  — "[see Warnings and Precautions ( 5.2 )]"
4. Inline section ref markers  — "( 1 )", "( 5.2 )", "( 2.1 , 2.4 )" scattered in prose
5. Adverse-reaction boilerplate— "To report SUSPECTED ADVERSE REACTIONS, contact ... medwatch."
6. Clinical-trial boilerplate  — "Because clinical trials are conducted under widely varying..."
7. Formula artifacts           — trailing "Chemical Structure", "Structural Formula", "Structure"
8. Duplicate sentences         — FDA labels often contain a full narrative + a repeated summary
9. drug_class [EPC] tags       — "Insulin Analog [EPC]" → "Insulin Analog"
10. Whitespace normalisation   — collapses runs of spaces/tabs

Run
───
    python clean_medication_jsons.py

Output
──────
    data/raw/medication_files_cleaned/*.json   (one file per drug, raw files untouched)

After running, point RAW_DIR in chunker_medicines.py to medication_files_cleaned/
and re-run the chunker to regenerate chunks from clean text.
"""

import json
import os
import re
from pathlib import Path

RAW_DIR     = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/raw/medication_files"
CLEANED_DIR = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/medication_files_cleaned"

# String fields whose values need text cleaning
TEXT_FIELDS = {
    "indications", "side_effects", "warnings", "precautions",
    "contraindications", "dosage", "drug_interactions",
    "overdose", "description", "storage",
}


# ── 1. Strip leading section headers ─────────────────────────────────────────

# Known FDA section-header names, matched case-insensitively.
# The optional prefix handles:
#   "1 INDICATIONS AND USAGE ..."       (section number only)
#   "6.1 Clinical Trials Experience..." (subsection number)
#   "INDICATIONS AND USAGE ..."         (no number, OTC style)
_HEADER_RE = re.compile(
    r'^(?:\d+(?:\.\d+)?\s+)?'      # optional "N " or "N.M " prefix
    r'(?:'
    r'INDICATIONS? AND USAGE|INDICATIONS?|USES?|'
    r'ADVERSE REACTIONS?|SIDE EFFECTS?|'
    r'WARNINGS? AND PRECAUTIONS?|WARNINGS?|PRECAUTIONS?|BOXED WARNINGS?|'
    r'CONTRAINDICATIONS?|'
    r'DOSAGE AND ADMINISTRATION|'
    r'DRUG INTERACTIONS?|INTERACTIONS?|'
    r'OVERDOSAGE|OVERDOSE|'
    r'DESCRIPTION|'
    r'STORAGE AND HANDLING|STORAGE|'
    r'CLINICAL PHARMACOLOGY|CLINICAL STUDIES|'
    r'HOW SUPPLIED|PATIENT COUNSELING INFORMATION|'
    r'USE IN SPECIFIC POPULATIONS|MECHANISM OF ACTION'
    r')\s+',
    re.IGNORECASE,
)


def strip_leading_header(text: str) -> str:
    """Remove the FDA section header from the start of a field value (one pass)."""
    return _HEADER_RE.sub("", text, count=1).strip()


# ── 2. Remove inline subsection number prefixes ───────────────────────────────

def remove_subsection_numbers(text: str) -> str:
    """
    Strip 'N.M ' numeric prefixes from sub-section titles that appear mid-text.
    E.g. '...at all. 6.1 Clinical Trials Experience Because...'
      →  '...at all. Clinical Trials Experience Because...'

    Only removes the digits — preserves the title text that follows.
    Guard: only fires before an uppercase letter to avoid clipping
    decimal measurements like '1.73 m2' or '0.25 mg'.
    """
    return re.sub(r"\b\d+\.\d+\s+(?=[A-Z])", "", text)


# ── 3. Remove [see ...] cross-references ─────────────────────────────────────

def remove_see_references(text: str) -> str:
    """
    Remove bracketed cross-reference links.
    Examples:
        [see Warnings and Precautions ( 5.2 )]
        [see Boxed Warning]
        [See Clinical Pharmacology (12.3)]
        [ see Dosage and Administration ( 2.1 , 2.2 )]
    """
    return re.sub(r"\[\s*see[^\]]*\]", "", text, flags=re.IGNORECASE)


# ── 4. Remove ( N ) inline section reference markers ─────────────────────────

def remove_inline_refs(text: str) -> str:
    """
    Remove parenthetical FDA section-number references embedded in prose.
    Pattern: ( N ), ( N.M ), ( N.M , N.M , N.M ) — always have at least one
    space inside, which distinguishes them from dosage values like (2 mg).

    Safe against:
        (N=268)           — contains letters
        (2 to 3)          — "to" breaks the pattern
        (eGFR below 30)   — starts with a letter
        (400 mg)          — "mg" breaks the pattern
    """
    return re.sub(
        r"\(\s*\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*\s*\)",
        "",
        text,
    )


# ── 5. Remove adverse-reaction reporting boilerplate ─────────────────────────

_REPORT_RE = re.compile(
    r"To report SUSPECTED ADVERSE REACTIONS[^.]*?"
    r"(?:www\.fda\.gov/medwatch\.?|fda\.gov/medwatch\.?|medwatch\.)",
    re.IGNORECASE | re.DOTALL,
)


def remove_reporting_boilerplate(text: str) -> str:
    """Remove 'To report SUSPECTED ADVERSE REACTIONS, contact ... medwatch.' lines."""
    return _REPORT_RE.sub("", text)


# ── 6. Remove clinical-trial disclaimer boilerplate ──────────────────────────

_CT_BOILERPLATE_RE = re.compile(
    r"Because clinical trials are conducted under widely varying conditions[^.]+\.",
    re.IGNORECASE,
)


def remove_clinical_trial_boilerplate(text: str) -> str:
    """
    Remove the standard FDA clinical-trial-comparability disclaimer.
    Appears verbatim in nearly every side_effects / adverse_reactions field.
    """
    return _CT_BOILERPLATE_RE.sub("", text)


# ── 7. Remove structural formula artifacts ────────────────────────────────────

_FORMULA_ARTIFACT_RE = re.compile(
    r"\b(?:Chemical\s+Structure|Structural\s+Formula|Structure\s+Structure|Structure)\s*$",
    re.IGNORECASE,
)


def remove_formula_artifacts(text: str) -> str:
    """
    Remove trailing placeholder labels left by PDF-to-text conversion of
    chemical structure images.  Examples seen in description fields:
        '...C 25 H 29 I 2 NO 3 ∙ HCl Molecular Weight: 681.8  Chemical Structure'
        '...The structural formula is as follows: ... Structural Formula'
        '...Structure Structure'
    """
    return _FORMULA_ARTIFACT_RE.sub("", text).strip()


# ── 8. Deduplicate sentences ──────────────────────────────────────────────────

def deduplicate_sentences(text: str) -> str:
    """
    Remove repeated sentences within a field.

    FDA labels frequently contain a full narrative section followed by a
    condensed highlights/summary section that repeats the same sentences.
    Only exact matches longer than 40 characters are deduplicated, so short
    transitional phrases that appear more than once are left intact.
    """
    # Split at sentence boundaries: period/!/? followed by whitespace + capital letter
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
    seen: set[str] = set()
    kept = []
    for part in parts:
        key = re.sub(r"\s+", " ", part.strip().lower())
        if len(key) > 40 and key in seen:
            continue
        if len(key) > 40:
            seen.add(key)
        kept.append(part)
    return " ".join(kept)


# ── 9. Clean drug_class entries ───────────────────────────────────────────────

def clean_drug_class(values: list) -> list:
    """
    Strip FDA classification tags appended to drug_class list entries.
    Example: 'Insulin Analog [EPC]' → 'Insulin Analog'
    """
    result = []
    for v in values:
        v = re.sub(r"\s*\[EPC\]\s*", "", v, flags=re.IGNORECASE).strip()
        if v:
            result.append(v)
    return result


# ── 10. Whitespace normalisation ──────────────────────────────────────────────

def normalize_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs to a single space; shrink 3+ newlines to 2."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Master text cleaner ───────────────────────────────────────────────────────

def clean_text_field(text: str) -> str:
    """Apply all text cleaners in order to a single field value."""
    if not text or not text.strip():
        return ""
    text = strip_leading_header(text)
    text = remove_subsection_numbers(text)
    text = remove_see_references(text)
    text = remove_inline_refs(text)
    text = remove_reporting_boilerplate(text)
    text = remove_clinical_trial_boilerplate(text)
    text = remove_formula_artifacts(text)
    text = deduplicate_sentences(text)
    text = normalize_whitespace(text)
    return text


# ── Drug-level cleaner ────────────────────────────────────────────────────────

# Fields considered essential for clinical usefulness
_QUALITY_FIELDS = ["indications", "side_effects", "dosage", "drug_interactions", "overdose"]

def data_quality_score(drug: dict) -> float:
    """
    Returns a 0.0–1.0 score based on how many essential clinical fields are
    populated after cleaning. Used downstream to decide whether to skip local
    generation and go straight to web fallback.
    """
    populated = sum(
        1 for f in _QUALITY_FIELDS
        if drug.get(f) and str(drug[f]).strip()
    )
    return round(populated / len(_QUALITY_FIELDS), 2)


def clean_drug(drug: dict) -> dict:
    """Return a cleaned copy of a drug dict (original is not mutated)."""
    cleaned = dict(drug)

    for field in TEXT_FIELDS:
        if field in cleaned and isinstance(cleaned[field], str):
            cleaned[field] = clean_text_field(cleaned[field])

    if "drug_class" in cleaned and isinstance(cleaned["drug_class"], list):
        cleaned["drug_class"] = clean_drug_class(cleaned["drug_class"])

    cleaned["data_quality"] = data_quality_score(cleaned)

    return cleaned


# ── Process all files ─────────────────────────────────────────────────────────

def process_all(preview: bool = False) -> None:
    """
    Clean every JSON file in RAW_DIR and write results to CLEANED_DIR.

    Args:
        preview: If True, print a before/after diff for the first drug
                 instead of writing files.
    """
    os.makedirs(CLEANED_DIR, exist_ok=True)
    files = sorted(Path(RAW_DIR).glob("*.json"))

    if not files:
        print(f"No JSON files found in {RAW_DIR}")
        return

    print(f"Cleaning {len(files)} files  →  {CLEANED_DIR}\n")

    for fp in files:
        with open(fp, encoding="utf-8") as f:
            drug = json.load(f)

        cleaned = clean_drug(drug)

        if preview:
            _print_diff(drug, cleaned)
            return  # only show first drug in preview mode

        out_path = Path(CLEANED_DIR) / fp.name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"Done.  {len(files)} files written to {CLEANED_DIR}")
    print()
    print("Next step: update RAW_DIR in chunker_medicines.py to point to")
    print(f"  {CLEANED_DIR}")
    print("then re-run the chunker.")


def _print_diff(raw: dict, cleaned: dict) -> None:
    """Print a side-by-side comparison of changed fields for one drug."""
    name = raw.get("generic_name", "unknown")
    print(f"=== PREVIEW: {name} ===\n")
    for field in sorted(set(raw) | set(cleaned)):
        r = raw.get(field, "")
        c = cleaned.get(field, "")
        if r == c:
            continue
        # Show first 300 chars of each
        print(f"  FIELD: {field}")
        print(f"  BEFORE: {str(r)[:300]!r}")
        print(f"  AFTER : {str(c)[:300]!r}")
        print()


if __name__ == "__main__":
    import sys
    preview_mode = "--preview" in sys.argv
    process_all(preview=preview_mode)
