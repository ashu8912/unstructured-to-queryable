"""Schema primitives shared across classification, extraction, and storage.

A "document type" is defined by a name (slug), a description, and a list of
FieldSpecs. Types live in the registry (see db.py); this module only knows how
to describe fields and turn them into a Pydantic model for schema-forced
extraction.
"""

import re
from typing import Optional, Literal, Any

from pydantic import BaseModel, create_model

# Supported field types. Kept deliberately small so both the LLM and the
# SQLite view layer can map them unambiguously.
FieldType = Literal["string", "number", "integer", "boolean", "date", "list"]

# field type -> python type used for the dynamic Pydantic model
_PY_TYPE: dict[str, Any] = {
    "string": Optional[str],
    "number": Optional[float],
    "integer": Optional[int],
    "boolean": Optional[bool],
    "date": Optional[str],        # ISO YYYY-MM-DD, kept as a string
    "list": Optional[list[str]],  # simple lists (tags, item names)
}


class FieldSpec(BaseModel):
    """One labeled box in a document type's schema."""
    name: str
    type: FieldType
    description: str = ""


def slug(text: str) -> str:
    """Deterministic identifier so 'Store Receipt' and 'store receipt' collide."""
    s = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return s or "unnamed"


def build_model(type_name: str, fields: list[FieldSpec]) -> type[BaseModel]:
    """Create a Pydantic model from field specs for schema-forced extraction."""
    definitions = {slug(f.name): (_PY_TYPE[f.type], None) for f in fields}
    return create_model(slug(type_name).title().replace("_", ""), **definitions)