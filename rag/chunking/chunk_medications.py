"""
Build MedicationChunk records from cleaner (metadata dict, prose dict) tuples.

Prose buckets: usage → safety → interaction → storage (non-empty bundles only).

Secondary RecursiveCharacter splitting (tiktoken-aware) activates only beyond threshold.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from rag.config import MEDICATION_SECONDARY_SPLIT_THRESHOLD

from .schemas import MedicationChunk
from .text_splitter_factory import (
    create_medication_text_splitter,
    medication_group_token_length,
)

logger = logging.getLogger(__name__)

ChunkTypeKey = Literal["usage", "safety", "interaction", "storage"]

USAGE_FIELDS = ("indications", "dosage", "description")
SAFETY_FIELDS = ("side_effects", "warnings", "precautions", "contraindications", "overdose")
INTERACTION_FIELDS = ("drug_interactions",)
STORAGE_FIELDS = ("storage",)

GROUP_SPECS: tuple[tuple[ChunkTypeKey, tuple[str, ...]], ...] = (
    ("usage", USAGE_FIELDS),
    ("safety", SAFETY_FIELDS),
    ("interaction", INTERACTION_FIELDS),
    ("storage", STORAGE_FIELDS),
)


def _string_list(meta: dict[str, Any], key: str) -> list[str]:
    """Normalize list-valued metadata safely for chunk payloads."""
    value = meta.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    out = str(value).strip()
    return [out] if out else []


def _combine_labeled_groups(prose: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Join selected prose paragraphs with canonical field labels."""
    blocks: list[str] = []
    for key in keys:
        blob = prose.get(key)
        if isinstance(blob, str) and blob.strip():
            nice = key.replace("_", " ").upper()
            blocks.append(f"{nice}: {blob.strip()}")
    return "\n\n".join(blocks).strip()


def chunk_medications(rows: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[MedicationChunk]:
    """Produce MedicationChunk objects with ordered chunk_type buckets per drug."""
    splitter = create_medication_text_splitter()
    emitted: list[MedicationChunk] = []

    for meta, prose in rows:
        gn_raw = meta.get("generic_name")
        if gn_raw is None:
            generic: str | None = None
        elif isinstance(gn_raw, str):
            generic = gn_raw.strip() or None
        else:
            generic = str(gn_raw).strip() or None
        manufacturers = meta.get("manufacturer")
        manufacturer_val = manufacturers if isinstance(manufacturers, str) else None
        brands = _string_list(meta, "brand_names")
        classes = _string_list(meta, "drug_class")

        chunk_serial = 0
        label = generic or prose.get("description", "")[:32] or "unknown-drug"

        for chunk_type, field_keys in GROUP_SPECS:
            bundle = _combine_labeled_groups(prose, field_keys)
            if not bundle:
                logger.debug("Skipping empty %s group for %s", chunk_type, label)
                continue

            threshold = MEDICATION_SECONDARY_SPLIT_THRESHOLD
            if medication_group_token_length(bundle) > threshold:
                pieces = splitter.split_text(bundle)
            else:
                pieces = [bundle]

            for fragment in pieces:
                trimmed = fragment.strip()
                if not trimmed:
                    continue
                emitted.append(
                    MedicationChunk(
                        text=trimmed,
                        generic_name=generic,
                        brand_names=brands,
                        drug_class=classes,
                        manufacturer=manufacturer_val,
                        chunk_type=chunk_type,
                        chunk_index=chunk_serial,
                    )
                )
                chunk_serial += 1

        logger.debug(
            "chunk_medications emitted %s slice(s) for drug key=%s",
            chunk_serial,
            generic or label,
        )

    logger.info(
        "chunk_medications complete: %s total chunks across %s drugs.",
        len(emitted),
        len(rows),
    )
    return emitted
