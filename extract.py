"""Phase 2: extract fields for a known type.

The type's schema (its FieldSpecs) is turned into a Pydantic model and passed as
response_schema, so the model fills *our* boxes instead of free-forming JSON.
"""

from google.genai import types

from llm import client, MODEL
from schema import FieldSpec, build_model


def extract_document(file_bytes: bytes, mime_type: str,
                     type_name: str, fields: list[FieldSpec]) -> dict:
    model_cls = build_model(type_name, fields)
    field_hint = ", ".join(f"{f.name} ({f.type})" for f in fields)
    resp = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            f"Extract these fields: {field_hint}. "
            "Use YYYY-MM-DD for dates. Return null for anything you can't find.",
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=model_cls,
        ),
    )
    return model_cls.model_validate_json(resp.text).model_dump()