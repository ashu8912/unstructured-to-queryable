# P3 — Decisions

## What P3 is

Build a pipeline that takes an **unstructured** document (image or PDF), figures
out **what kind of document it is**, extracts it into that type's **schema**, and
makes the result **queryable**. It handles many document types, not one: a
registry of known types grows as new kinds of documents show up.

Flow: `upload → classify → (confirm new type) → extract (schema-forced) → store → query`.

## Scope decisions (why narrowed this way)

- **Any document type, discovered on the fly.** Instead of hardcoding one
  schema, the system keeps a **registry** of document types and classifies each
  upload into an existing type or proposes a new one. Receipts are just the
  first type it learns.
- **Vision model instead of OCR.** Gemini reads the image/PDF directly, so no
  OCR engine to install or tune. Removes the biggest setup hurdle for a first
  build.
- **Two-phase pipeline (classify, then extract).** Deciding *what a document is*
  and *pulling its fields out* are separate jobs. Splitting them keeps schemas
  consistent and stops the model from hedging.
- **Schema-constrained output.** The chosen type's fields are turned into a
  Pydantic model passed as `response_schema`, forcing the model to fill *our*
  fields instead of free-forming JSON.
- **JSON storage + per-type views.** Rows are stored as JSON in one `documents`
  table; each type gets a SQL view projecting its fields as columns. Stays
  queryable without destructive migrations when a type evolves.
- **New types are gated.** Creating a type is a schema change, so it requires a
  confidence threshold and explicit user confirmation — this prevents table
  sprawl and near-duplicate types.
- **SQLite, not a server DB.** Built into Python, zero setup, SQL for free.
- **Streamlit for the UI.** Upload, classify, confirm, browse, and query with
  minimal frontend code.

## The stack

| Piece | Choice | Why |
|-------|--------|-----|
| Language | Python 3.10+ | Fits all libs below |
| Extraction | `google-genai` (Gemini Flash) | Free tier, reads image/PDF, no GPU |
| Schema | `pydantic` | Defines fields *and* constrains model output |
| Storage | `sqlite3` | Stdlib, queryable via SQL |
| UI | `streamlit` | Upload + tables + query box, minimal code |
| Display | `pandas` | Render query results as tables |

## Architecture (registry-driven, two-phase)

- `doc_types` — the **registry**: one row per known type (name, description,
  field specs). The source of truth the classifier is grounded in.
- `documents` — uniform storage: every extraction is a JSON payload tagged with
  its type. No per-type row schema, so evolving a type needs no migration.
- `view_<type>` — a SQL view per type projecting JSON fields as real columns, so
  each type stays cleanly queryable.
- **Phase 1 (classify):** the model sees the registry and returns an existing
  type or proposes a new one, with a confidence score.
- **Phase 2 (extract):** the chosen type's fields become a Pydantic model used
  as `response_schema`.
- **Gate:** new types (or low-confidence matches) require user confirmation
  before a view/table is created.

## Field types (the vocabulary)

A type's schema is a list of fields, each one of: `string`, `number`,
`integer`, `boolean`, `date` (ISO string), or `list` (list of strings). Kept
small so both the model and the SQLite view layer map them unambiguously.
Nested/structured children (e.g. per-item amounts) are out of scope for v1.

## Open items / risks

- **Model ID drifts.** Free Flash model string changes; currently
  `gemini-flash-latest`. Confirm the live id in Google AI Studio.
- **Query surface is raw SQL.** The UI passes a user WHERE clause straight to
  SQLite — fine for a local single-user build, but not safe to expose.
  A natural-language → SQL layer is the obvious next step.
- **Type sprawl still possible.** Confirmation + slug collision + confidence
  gate reduce near-duplicate types, but a human can still confirm a bad one.
  A merge/rename tool for the registry would help.
- **No schema evolution yet.** If a type gains a field later, old rows just
  return null for it; there's no re-extraction or field deprecation flow.
- **Scalar/list fields only.** Structured children (line items with amounts)
  aren't modeled; would need nested types or a child table.
- **No validation of extracted values** beyond field types (dates, totals
  aren't sanity-checked).

## Next steps

1. Confirm the current Flash model id and get a free API key.
2. Run a mix of document types through it, check classification + extraction.
3. Add a registry merge/rename tool to curate types.
4. Add value validation (date parsing, numeric ranges).
5. Consider a natural-language query box over the raw SQL input.
