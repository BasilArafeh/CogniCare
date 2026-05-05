"""
Pydantic schema for validating medicine JSON documents on load.

Single source of truth for allowable fields on a MedicineDocument.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class MedicineDocument(BaseModel):
    """
    One drug record as stored in medicines/*.json.

    All fields are optional with default None so partial or evolving files validate.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=False)

    generic_name: Optional[str] = None
    brand_names: Optional[list[str]] = None
    fda_brand_names: Optional[list[str]] = None
    manufacturer: Optional[str] = None
    drug_class: Optional[list[str]] = None
    indications: Optional[str] = None
    side_effects: Optional[str] = None
    warnings: Optional[str] = None
    precautions: Optional[str] = None
    contraindications: Optional[str] = None
    dosage: Optional[str] = None
    drug_interactions: Optional[str] = None
    overdose: Optional[str] = None
    description: Optional[str] = None
    storage: Optional[str] = None

    @field_validator(
        "brand_names",
        "fda_brand_names",
        "drug_class",
        mode="before",
    )
    @classmethod
    def _coerce_str_list(cls, value: Any) -> Any:
        """Normalize list-like JSON values (sometimes a bare string slips in)."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else None
        if isinstance(value, list):
            out = [str(x).strip() for x in value if str(x).strip()]
            return out or None
        return value
