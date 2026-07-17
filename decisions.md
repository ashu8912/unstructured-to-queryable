# P3 — Decisions

## What P3 is

Build a pipeline that takes an **unstructured** document (a receipt image or PDF),
turns it into **structured** rows using a fixed **schema**, and makes the result
**queryable**. Receipts are the first target because they're semi-structured:
every one has a store, date, and total, but the layout differs per vendor.

Flow: `upload → extract (schema-forced) → store → query`.

## Scope decisions (why narrowed this way)

- **One document type first (receipts).** Semi-structured and easy to reason
  about. Nails the end-to-end path before generalizing to invoices/forms.
- **Vision model instead of OCR.** Gemini reads the image/PDF directly, so no
  OCR engine to install or tune. Removes the biggest setup hurdle for a first
  build.
- **Schema-constrained output.** The Pydantic `Receipt` model is passed as
  `response_schema`, forcing the model to fill *our* fields instead of
  free-forming JSON. This is what makes output reliable enough to store.
- **SQLite, not a server DB.** Built into Python, zero setup, and SQL gives us
  "queryable" for free. Swap for Postgres later if needed.
- **Streamlit for the UI.** Free file upload, tables, and query box with almost
  no frontend code. Good enough to demo the whole left-to-right journey.

## The stack

| Piece | Choice | Why |
|-------|--------|-----|
| Language | Python 3.10+ | Fits all libs below |
| Extraction | `google-genai` (Gemini Flash) | Free tier, reads image/PDF, no GPU |
| Schema | `pydantic` | Defines fields *and* constrains model output |
| Storage | `sqlite3` | Stdlib, queryable via SQL |
| UI | `streamlit` | Upload + tables + query box, minimal code |
| Display | `pandas` | Render query results as tables |

## Schema (the contract)

`Receipt`: `store`, `date` (YYYY-MM-DD), `total`, `currency`, `items[]`
where each `LineItem` is `description` + `amount`. All top-level fields are
optional so the model can return null instead of hallucinating.

## Open items / risks

- **Model ID drifts.** Free Flash model string changes; currently
  `gemini-flash-latest`. Confirm the live id in Google AI Studio.
- **Query surface is raw SQL.** The UI passes a user WHERE clause straight to
  SQLite — fine for a local single-user build, but not safe to expose.
  A natural-language → SQL layer is the obvious next step.
- **No validation of extracted values** beyond schema types (e.g. dates,
  totals aren't sanity-checked yet).
- **Line items are stored as JSON blob**, not queryable rows. Normalize into a
  separate table if item-level queries are needed.

## Next steps

1. Confirm the current Flash model id and get a free API key.
2. Run the pipeline on a handful of real receipts, check extraction quality.
3. Add basic value validation (date parsing, total ≥ 0).
4. Consider a natural-language query box over the raw SQL input.
