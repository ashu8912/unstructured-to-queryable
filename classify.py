"""Phase 1: classify a document against the registry.

The model is *grounded* in the existing types (it sees their names, descriptions,
and fields) and must either match one of them or propose a brand-new type. It
never sees the raw table list from nowhere — the registry is the source of truth,
which is what stops it from hallucinating matches or inventing near-duplicates.
"""

from typing import Literal

from pydantic import BaseModel
from google.genai import types

from llm import generate
from schema import FieldSpec


class Decision(BaseModel):
    match: Literal["existing", "new"]
    type_name: str            # existing slug, or a proposed slug for a new type
    description: str = ""      # only meaningful when match == "new"
    fields: list[FieldSpec] = []   # proposed schema when match == "new"
    confidence: float         # 0..1, how sure the model is about the match
    reasoning: str = ""


def _registry_prompt(registry: list[dict]) -> str:
    if not registry:
        return "There are no existing document types yet."
    lines = ["Existing document types (match one of these if it fits):"]
    for t in registry:
        fnames = ", ".join(f"{f.name}:{f.type}" for f in t["fields"])
        lines.append(f"- {t['name']}: {t['description']} | fields: {fnames}")
    return "\n".join(lines)


def classify_document(file_bytes: bytes, mime_type: str, registry: list[dict]) -> Decision:
    resp = generate(
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            _registry_prompt(registry),
            "Decide which existing type this document belongs to. "
            "If none fit, set match='new' and propose a concise snake_case "
            "type_name, a one-line description, and a minimal field list "
            "(name, type in [string, number, integer, boolean, date, list], "
            "description). Only propose 'new' when no existing type is a good "
            "fit. Report your confidence between 0 and 1.",
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Decision,
        ),
    )
    return Decision.model_validate_json(resp.text)
