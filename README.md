# unstructured-to-queryable

> Turn a shoebox of receipts into a table you can ask questions.

Drop in a receipt (image or PDF), and this pipeline reads it, forces the output
into a fixed schema, stores it in SQLite, and lets you query it with SQL — no
OCR engine, no GPU, no manual data entry.

```
 upload  ─▶  extract  ─▶  store  ─▶  query
 (image/    (schema-      (SQLite)   (SQL over
  PDF)       forced LLM)              your rows)
```

---

## Why

Receipts are **semi-structured**: every one has a store, a date, and a total —
but the layout changes per vendor, so a computer can't reliably find them. This
project builds the machine that takes that messy, human-readable input and turns
it into clean, **queryable** rows.

- **Unstructured** — a photo of a receipt; information with no consistent place.
- **Schema** — the labeled boxes you decide on: `store`, `date`, `amount`.
- **Structured** — the data poured into that neat, labeled table.
- **Queryable** — you can now ask *"show me every receipt over $40"* and get an
  instant answer.

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
| `schema.py`     | The `Receipt` schema — the contract everything else obeys   |
| `extract.py`    | Unstructured file → structured `Receipt` (schema-forced)    |
| `db.py`         | SQLite storage + query helpers                              |
| `app.py`        | Streamlit UI: upload, extract, browse, query                |
| `list_models.py`| Helper to list available Gemini models                      |
| `decisions.md`  | Scope, stack, and risk decisions for the build              |

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

Drop a current Flash id into the `MODEL` constant in `extract.py` if needed.

**5. Run the app**

```bash
streamlit run app.py
```

---

## Usage

1. Upload a receipt (`.pdf`, `.png`, `.jpg`).
2. Click **Extract** — the model fills the schema and the row is saved.
3. Browse your receipts in the table.
4. Ask questions with a SQL `WHERE` clause, e.g. `total > 40`.

---

## Schema

```python
class LineItem(BaseModel):
    description: str
    amount: float

class Receipt(BaseModel):
    store: Optional[str] = None
    date: Optional[str] = None        # YYYY-MM-DD
    total: Optional[float] = None
    currency: Optional[str] = None
    items: list[LineItem] = []
```

All top-level fields are optional so the model returns `null` instead of
hallucinating a value it can't find.

---

## Roadmap

- [ ] Validate extracted values (parse dates, enforce `total >= 0`)
- [ ] Natural-language → SQL query box (replace raw `WHERE` input)
- [ ] Normalize line items into their own queryable table
- [ ] Generalize beyond receipts to invoices and forms

---

## Notes & limitations

- The query box passes a raw SQL `WHERE` clause to SQLite — fine for a local,
  single-user build, **not** safe to expose publicly.
- Extraction quality depends on the model; always spot-check results.
