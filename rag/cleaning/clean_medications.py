"""
Load medicines/*.json files, validate, normalize strings, split metadata vs embeddable prose.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

import ftfy

from .medicine_schema import MedicineDocument

logger = logging.getLogger(__name__)

METADATA_FIELDS = frozenset(
    {"generic_name", "brand_names", "fda_brand_names", "drug_class", "manufacturer"},
)
PROSE_FIELDS = frozenset(
    {
        "indications",
        "side_effects",
        "warnings",
        "precautions",
        "contraindications",
        "dosage",
        "drug_interactions",
        "overdose",
        "description",
        "storage",
    },
)


def _is_empty_scalar(value: Any) -> bool:
    """Treat None, blank strings, and empty containers as removable."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _drop_empty_nested(obj: Any) -> Any:
    """Remove empty-string and empty-list keys from dicts/lists recursively."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if _is_empty_scalar(v):
                continue
            pruned = _drop_empty_nested(v)
            if not _is_empty_scalar(pruned):
                out[k] = pruned
        return out
    if isinstance(obj, list):
        out_list = []
        for item in obj:
            if _is_empty_scalar(item):
                continue
            pruned_item = _drop_empty_nested(item)
            if not _is_empty_scalar(pruned_item):
                out_list.append(pruned_item)
        return out_list
    return obj


_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
_REPEAT_SPACES_RE = re.compile(r"[ \t]{2,}")


def _clean_string(text: str) -> str:
    """Apply ftfy and tidy spacing around punctuation for embedding-friendly prose."""
    if not text:
        return ""
    fixed = ftfy.fix_text(text)
    normalized = fixed.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _REPEAT_SPACES_RE.sub(" ", normalized)
    normalized = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", normalized)
    lines = [ln.strip() for ln in normalized.splitlines()]
    normalized = "\n".join(lines)
    normalized = _REPEAT_SPACES_RE.sub(" ", normalized)
    return normalized.strip()


def _clean_nested_strings(obj: Any) -> Any:
    """Walk dict/list tree and apply _clean_string to all string leaf values."""
    if isinstance(obj, str):
        return _clean_string(obj)
    if isinstance(obj, dict):
        return {k: _clean_nested_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nested_strings(x) for x in obj]
    return obj


def _split_metadata_prose(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate filter/join-friendly metadata dict from prose fields for embeddings."""
    meta = {k: payload[k] for k in METADATA_FIELDS if k in payload}
    prose = {k: payload[k] for k in PROSE_FIELDS if k in payload}
    return meta, prose


def _parse_one_file(path: Path) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Load and clean a single medicines JSON path; logs and returns None on failure."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read/parse medicines JSON: %s", path)
        return None, None

    try:
        doc = MedicineDocument.model_validate(raw)
    except Exception:
        logger.exception("Validation failed for medicines JSON: %s", path)
        return None, None

    dumped = doc.model_dump(exclude_none=True, mode="python")
    pruned = _drop_empty_nested(dumped)
    if not isinstance(pruned, dict):
        logger.warning("Unexpected non-dict payload after prune: %s", path)
        return None, None
    normalized = _clean_nested_strings(pruned)
    final = _drop_empty_nested(normalized)
    if not isinstance(final, dict):
        logger.warning("Unexpected non-dict payload after string cleaning: %s", path)
        return None, None
    meta, prose = _split_metadata_prose(final)
    logger.info(
        "Loaded medicine record from %s (generic_name=%s, prose_fields=%s).",
        path.name,
        meta.get("generic_name"),
        sorted(prose.keys()),
    )
    return meta, prose


def load_and_clean_all_medication_files(medicines_dir: Path) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Load every *.json file in the medicines directory and return cleaned split dicts."""
    root = medicines_dir.resolve()
    if not root.is_dir():
        logger.warning("Medicines directory does not exist: %s", root)
        return []

    outputs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    json_files = sorted(root.glob("*.json"))
    logger.info("Found %s JSON files under %s.", len(json_files), root)

    for path in json_files:
        meta, prose = _parse_one_file(path)
        if meta is None and prose is None:
            logger.error("Skipping unparseable file: %s", path.name)
            continue
        outputs.append((meta or {}, prose or {}))

    logger.info("Successfully cleaned %s medicine records.", len(outputs))
    return outputs
