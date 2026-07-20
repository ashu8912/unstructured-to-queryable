"""Registry-driven storage.

- `doc_types`  : the registry. One row per known document type (the schema).
- `documents`  : uniform storage. Every extracted document is a JSON payload
                 tagged with its type. No per-type row schema, so evolving a
                 type never requires a destructive migration.
- `view_<type>`: a SQL view per type that projects the JSON fields as real
                 columns, so each type stays cleanly queryable.
"""

import json
import sqlite3

from schema import FieldSpec, slug

DB = "documents.db"


def _connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = _connect()
    con.execute("""
        CREATE TABLE IF NOT EXISTS doc_types (
            name        TEXT PRIMARY KEY,
            description TEXT,
            fields_json TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        )""")
    con.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type    TEXT NOT NULL REFERENCES doc_types(name),
            source_name TEXT,
            extracted_at TEXT DEFAULT (datetime('now')),
            data_json   TEXT NOT NULL
        )""")
    con.commit()
    con.close()


# --- registry -------------------------------------------------------------

def list_types() -> list[dict]:
    con = _connect()
    rows = con.execute(
        "SELECT name, description, fields_json FROM doc_types ORDER BY name"
    ).fetchall()
    con.close()
    return [
        {"name": r["name"],
         "description": r["description"],
         "fields": [FieldSpec(**f) for f in json.loads(r["fields_json"])]}
        for r in rows
    ]


def get_type(name: str) -> dict | None:
    for t in list_types():
        if t["name"] == name:
            return t
    return None


def type_exists(name: str) -> bool:
    return get_type(slug(name)) is not None


def register_type(name: str, description: str, fields: list[FieldSpec]) -> str:
    """Add a new document type to the registry and create its view. Idempotent."""
    name = slug(name)
    con = _connect()
    con.execute(
        "INSERT OR IGNORE INTO doc_types (name, description, fields_json) "
        "VALUES (?, ?, ?)",
        (name, description, json.dumps([f.model_dump() for f in fields])),
    )
    con.commit()
    con.close()
    _rebuild_view(name, fields)
    return name


def _rebuild_view(name: str, fields: list[FieldSpec]):
    cols = ", ".join(
        f"json_extract(data_json, '$.{slug(f.name)}') AS {slug(f.name)}"
        for f in fields
    )
    con = _connect()
    con.execute(f'DROP VIEW IF EXISTS "view_{name}"')
    con.execute(
        f'CREATE VIEW "view_{name}" AS '
        f"SELECT id, source_name, extracted_at{', ' + cols if cols else ''} "
        f"FROM documents WHERE doc_type = '{name}'"
    )
    con.commit()
    con.close()


# --- documents ------------------------------------------------------------

def insert_document(doc_type: str, source_name: str, data: dict) -> int:
    con = _connect()
    cur = con.execute(
        "INSERT INTO documents (doc_type, source_name, data_json) VALUES (?, ?, ?)",
        (slug(doc_type), source_name, json.dumps(data)),
    )
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return new_id


def run_query(sql: str) -> list[dict]:
    con = _connect()
    rows = con.execute(sql).fetchall()
    con.close()
    return [dict(r) for r in rows]


def run_query_readonly(sql: str) -> list[dict]:
    """Execute a query over a physically read-only connection (defense in depth)."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(sql).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


# --- metrics & curation ---------------------------------------------------

def total_documents() -> int:
    con = _connect()
    n = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    con.close()
    return n


def type_counts() -> dict[str, int]:
    con = _connect()
    rows = con.execute(
        "SELECT doc_type AS name, COUNT(*) AS n FROM documents GROUP BY doc_type"
    ).fetchall()
    con.close()
    return {r["name"]: r["n"] for r in rows}


def delete_type(name: str) -> None:
    """Remove a type, its view, and all its documents. Destructive."""
    name = slug(name)
    con = _connect()
    con.execute(f'DROP VIEW IF EXISTS "view_{name}"')
    con.execute("DELETE FROM documents WHERE doc_type = ?", (name,))
    con.execute("DELETE FROM doc_types WHERE name = ?", (name,))
    con.commit()
    con.close()