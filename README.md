# unstructured-to-queryable

> Turn any pile of documents into tables you can ask questions.

**🌐 Live:** [ashughildiyal.cloud](https://ashughildiyal.cloud)

Drop in a document (image or PDF). The pipeline figures out **what kind of
document it is**, extracts it into that type's schema, stores it in SQLite, and
lets you query it with SQL — no OCR engine, no GPU, no manual data entry. New
document types are learned on the fly and added to a registry.

```
 upload  ─▶  classify  ─▶  extract  ─▶  store  ─▶  query
 (image/    (match a       (schema-     (SQLite    (SQL over
  PDF)       known type     forced LLM)  + views)   per-type
             or propose                             columns)
             a new one)
```

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

| File            | Role                                                        |
| --------------- | ----------------------------------------------------------- |
| `schema.py`     | Field types + dynamic Pydantic model builder                |
| `classify.py`   | Phase 1: classify a document against the registry           |
| `extract.py`    | Phase 2: extract fields for the chosen type (schema-forced) |
| `db.py`         | Registry, JSON storage, and per-type SQL views              |
| `llm.py`        | Shared Gemini client + model id                             |
| `app.py`        | Streamlit UI: upload, classify, confirm, browse, query      |
| `list_models.py`| Helper to list available Gemini models                      |
| `decisions.md`  | Scope, architecture, and risk decisions                     |

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

Drop a current Flash id into the `MODEL` constant in `llm.py` if needed.

**5. Run the app**

```bash
streamlit run app.py
```

---

## Usage

1. Upload a document (`.pdf`, `.png`, `.jpg`).
2. Click **Analyze** — it's classified against known types.
3. If it matches a known type confidently, it's extracted and saved. If it's a
   new type (or a low-confidence match), you're shown the proposed schema and
   confirm before the type is created.
4. Browse each type's rows, or ask questions with a SQL `WHERE` clause.

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
- [ ] Natural-language → SQL query box (replace raw `WHERE` input)
- [ ] Nested/structured children (e.g. line items with per-item amounts)
- [ ] Schema evolution / re-extraction when a type gains fields

---

## Notes & limitations

- The query box passes a raw SQL `WHERE` clause to SQLite — fine for a local,
  single-user build, **not** safe to expose publicly.
- Extraction quality depends on the model; always spot-check results.
