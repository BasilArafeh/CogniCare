"""Stable output shapes produced by chunking before embedding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class MedicalChunk:
    """One embeddable slice of cleaned medical PDF text with provenance."""

    text: str
    source_folder: str
    filename: str
    page_number: int
    section_title: str
    chunk_index: int


@dataclass(frozen=True, slots=True)
class MedicationChunk:
    """One embeddable slice of consolidated medication prose with taxonomy metadata."""

    text: str
    generic_name: str | None
    brand_names: list[str]
    drug_class: list[str]
    manufacturer: str | None
    chunk_type: Literal["usage", "safety", "interaction", "storage"]
    chunk_index: int
