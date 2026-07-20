# unstructured-to-queryable

> Turn any pile of documents into tables you can ask questions.

**🌐 Live:** [ashughildiyal.cloud](https://ashughildiyal.cloud)

Drop in a document (image or PDF). The pipeline figures out **what kind of
document it is**, extracts it into that type's schema, stores it in SQLite, and
lets you query it with SQL — no OCR engine, no GPU, no manual data entry. New
document types are learned on the fly and added to a registry.

```
 upload  ─▶  classify  ─▶  extract  ─▶  review  ─▶  store  ─▶  ask
 (image/    (match a       (schema-     (edit      (SQLite    (plain English
  PDF)       known type     forced LLM)  before     + views)   → read-only
             or propose                  saving)               SQL)
             a new one)
```

A polished, **Zamp-styled multi-page app**: extract with a human-in-the-loop
review step, explore your data with KPIs and charts, and query it in plain
English.

---

## Why

Most documents are **semi-structured**: a receipt always has a store, a date,
and a total — but the layout changes per vendor, so a computer can't reliably
find them. This project builds the machine that takes that messy, human-readable
input and turns it into clean, **queryable** rows — for *any* document type, not
just one.

- **Unstructured** — a photo of a document; information with no consistent place.
- **Schema** — the labeled boxes for a type: e.g. `store`, `date`, `amount`.
- **Structured** — the data poured into that neat, labeled table.
- **Queryable** — you can now ask *"show me every receipt over $40"* and get an
  instant answer.

### How it stays unambiguous

- A **registry** (`doc_types`) is the source of truth for known types. The
  classifier is grounded in it, so it matches real types instead of inventing
  near-duplicates.
- **Two phases:** classify *what* a document is, then extract its fields — two
  separate jobs, kept separate.
- **New types are gated** by a confidence threshold and your confirmation, so
  the table list doesn't sprawl.
- Rows are stored as **JSON + a per-type SQL view**, so a type can evolve
  without a destructive migration.

---

## Features

- **Multi-page UI** (`st.navigation`): Extract · Explore · Ask · Types.
- **Human-in-the-loop review** — edit every extracted field before it's saved.
- **Ask your data** — plain-English questions become a **read-only** SQL query
  (guarded: SELECT-only + a physically read-only connection), shown before it
  runs.
- **Explore** — KPI cards, per-type tables, a group-by chart, and CSV export.
- **Registry management** — view learned types and delete them (with confirm).
- **Resilient LLM layer** — retry with backoff, automatic model fallback on rate
  limits, and friendly error messages instead of tracebacks.

---

## Stack

| Piece        | Choice                      | Why                                        |
| ------------ | --------------------------- | ------------------------------------------ |
| Language     | Python 3.10+                | Fits the whole stack                       |
| Extraction   | `google-genai` (Gemini Flash) | Free tier, reads image/PDF directly, no OCR |
| Schema       | `pydantic`                  | Defines fields *and* constrains LLM output |
| Storage      | `sqlite3`                   | Stdlib, queryable via SQL                  |
| UI           | `streamlit`                 | Upload + tables + query box, minimal code  |
| Display      | `pandas`                    | Render results as tables                   |

---

## Project layout

| File                | Role                                                        |
| ------------------- | ----------------------------------------------------------- |
| `app.py`            | Entry point: `st.navigation` + shared setup                 |
| `app_pages/`        | Pages: `extract`, `explore`, `ask`, `types`                 |
| `schema.py`         | Field types + dynamic Pydantic model builder                |
| `classify.py`       | Phase 1: classify a document against the registry           |
| `extract.py`        | Phase 2: extract fields for the chosen type (schema-forced) |
| `ask.py`            | Natural-language → guarded read-only SQL                    |
| `db.py`             | Registry, JSON storage, per-type SQL views, read-only query |
| `llm.py`            | Gemini client + retry/backoff + model fallback              |
| `ui.py`             | Zamp-style theme helpers (hero, error box)                  |
| `.streamlit/config.toml` | Theme + 50MB upload cap                                |
| `list_models.py`    | Helper to list available Gemini models                      |
| `decisions.md`      | Scope, architecture, and risk decisions                     |

---

## Setup

**1. Get a free Gemini API key** from
[Google AI Studio](https://aistudio.google.com/) — no billing, no credit card.

**2. Create the environment**

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install streamlit google-genai python-dotenv pydantic pandas
```

**3. Add your key** to a `.env` file in the project root (git-ignored):

```
GEMINI_API_KEY=paste_your_key_here
```

**4. Confirm the current model id** (Gemini model names shift often):

```bash
python list_models.py
```

Set the model via env if needed (in `.env`), plus optional rate-limit fallbacks:

```
GEMINI_MODEL=gemini-flash-latest
GEMINI_FALLBACK_MODELS=gemini-2.0-flash,gemini-2.0-flash-lite
```

**5. Run the app**

```bash
streamlit run app.py
```

---

## Usage

1. **Extract** — upload a document (`.pdf`, `.png`, `.jpg`) and click *Analyze*.
   It's classified against known types (with a confidence score); new or
   low-confidence types are shown for confirmation.
2. **Review** — the model fills the fields; correct anything, then *Save*. You're
   taken to Explore with a confirmation toast.
3. **Explore** — browse each type's rows, see KPIs and a chart, export CSV.
4. **Ask** — ask a question in plain English; inspect the generated read-only
   SQL and its results.
5. **Types** — review the registry and delete types you no longer want.

---

## Schema model

Each document type is a list of fields, each one of:

| Field type | Stored as        |
| ---------- | ---------------- |
| `string`   | text             |
| `number`   | float            |
| `integer`  | int              |
| `boolean`  | bool             |
| `date`     | ISO `YYYY-MM-DD` |
| `list`     | list of strings  |

Types live in the `doc_types` registry; rows live in one `documents` table as
JSON, and each type gets a `view_<type>` exposing its fields as columns.

---

## Roadmap

- [ ] Registry merge/rename tool to curate types
- [ ] Value validation (parse dates, enforce numeric ranges)
- [ ] Nested/structured children (e.g. line items with per-item amounts)
- [ ] Schema evolution / re-extraction when a type gains fields
- [ ] Multi-user auth + per-user data isolation

---

## Notes & limitations

- **Ask** generates SQL via the LLM; it's constrained to a single `SELECT` and
  run over a read-only connection, but review the shown SQL before trusting it.
- The free Gemini tier has rate limits; the app retries and falls back across
  models, but enabling billing is the only way to fully remove the caps.
- Extraction quality depends on the model; the review step exists to catch
  mistakes before saving.
