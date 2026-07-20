"""Natural-language questions → a single read-only SQLite SELECT.

Two layers of safety:
1. The model is told to return only a read-only SELECT over one known view.
2. `_guard` rejects anything that isn't a single SELECT, and the query is run
   through a physically read-only connection (see db.run_query_readonly).
"""

import re

from pydantic import BaseModel
from google.genai import types

from llm import generate
from schema import FieldSpec, slug

_FORBIDDEN = (
    "insert", "update", "delete", "drop", "alter", "attach",
    "detach", "pragma", "create", "replace", "truncate", "vacuum",
)


class SQLQuery(BaseModel):
    sql: str


def text_to_sql(question: str, type_name: str, fields: list[FieldSpec]) -> str:
    view = f"view_{slug(type_name)}"
    cols = ", ".join(f"{slug(f.name)} ({f.type})" for f in fields)
    resp = generate(
        contents=[
            f'Table "{view}" has columns: id, source_name, extracted_at, {cols}. '
            f"Write ONE read-only SQLite SELECT that answers the question. "
            f"Select only from this table. Never write data. "
            f"Question: {question}",
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SQLQuery,
        ),
    )
    sql = SQLQuery.model_validate_json(resp.text).sql.strip().rstrip(";").strip()
    _guard(sql)
    return sql


def _guard(sql: str) -> None:
    low = sql.lower()
    if not low.startswith("select") and not low.startswith("with "):
        raise ValueError("Only SELECT queries are allowed.")
    if ";" in sql:
        raise ValueError("Only a single statement is allowed.")
    for kw in _FORBIDDEN:
        if re.search(rf"\b{kw}\b", low):
            raise ValueError(f"Disallowed keyword in query: {kw}")
