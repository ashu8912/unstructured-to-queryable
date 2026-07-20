# Decisions & Design Rationale

This document records **what** was built, **why** each choice was made, the
**alternatives** weighed, and the **edge cases and failure modes** considered.
It is meant to be read as the thinking behind the product, not just a changelog.

---

## 1. The problem, stated plainly

Most business documents are **semi-structured**. A receipt always contains a
store, a date, and a total — but *where* those sit on the page changes with every
vendor. The information is there; it just isn't in a place a computer can rely
on. The same is true of invoices, forms, business cards, tickets, and payslips.

The goal of P3 is to build the machine that walks a document across three states:

| State | What it means | Everyday analogy |
| ----- | ------------- | ---------------- |
| **Unstructured** | Information with no consistent, machine-readable position | A shoebox of receipts |
| **Structured** | The same information poured into labeled columns of a known type | A sorted spreadsheet |
| **Queryable** | You can ask questions and get instant answers instead of reading by hand | "Show every receipt over $40" |

A **schema** is the bridge: the set of labeled boxes (`store`, `date`, `amount`)
you decide on *before* sorting. The whole project is: **take the shoebox, sort it
into labeled tables using schemas, and let someone query it — automatically, for
any document type.**

---

## 2. What we optimized for

These principles drove the trade-offs below, in priority order:

1. **Unambiguous over clever.** A predictable, inspectable system beats a
   magical one that occasionally invents nonsense.
2. **Small, cheap, no-infra first build.** Free API tier, no GPU, no OCR engine,
   stdlib storage. Prove the end-to-end path before adding weight.
3. **Reliability of extracted data.** Output must be trustworthy enough to store
   and query — so we constrain the model rather than hope it behaves.
4. **Generalizable, not hardcoded.** The system should learn new document types,
   not require a developer to add each one.
5. **Reversible where possible; gated where not.** Cheap actions run freely;
   schema changes (which are effectively irreversible) require confirmation.

---

## 3. Core decisions

### 3.1 Vision LLM instead of OCR + parsing

**Decision:** Send the raw image/PDF bytes to Gemini and let it read the document
directly.

**Why:** A traditional pipeline is OCR (Tesseract) → layout heuristics → field
matching. Each stage needs tuning and breaks on new layouts. A multimodal model
collapses all of that into one call and generalizes across layouts for free.

**Alternatives considered:**
- *Tesseract + regex/heuristics* — brittle per-vendor rules, heavy setup, poor
  generalization. Rejected for a first build.
- *Cloud Document AI (AWS Textract / Google Document AI)* — strong, but costs
  money, adds vendor lock-in, and is overkill before product-market fit.

**Trade-off accepted:** We inherit the model's failure modes (hallucination,
misreads) and its non-determinism. We mitigate this with schema-forcing (3.2)
and value nullability (3.6).

### 3.2 Schema-forced extraction, not free-form JSON

**Decision:** Turn the chosen type's fields into a Pydantic model and pass it as
`response_schema` so the model must return exactly those fields.

**Why:** "Extract the fields as JSON" invites the model to rename keys, nest
things differently, or invent fields — none of which is storable without
post-hoc cleanup. Constraining the output schema makes the result **shaped like
the table it's going into**. This is the single most important reliability lever
in the system.

**Edge case:** The model can still put a *wrong value* in the right box (a
misread total). Schema-forcing guarantees *shape*, not *correctness* — value
validation is a separate, still-open concern (see §6).

### 3.3 Many types via a registry, not one hardcoded schema

**Decision:** Keep a **registry** of document types (`doc_types`). Each upload is
classified into an existing type or becomes a new one. Receipts are just the
first type the system happens to learn.

**Why:** Hardcoding `Receipt` solves one document and nothing else. Real
document piles are heterogeneous. A registry lets the system grow its own
vocabulary of types over time without code changes.

**This is where the original idea needed scrutiny.** The naïve version — *"let
the AI look at a document and make a table for it"* — sounds right but is
ambiguous and produces sprawl. The corrections:

- **Match-first, generate-rarely.** If the model invents a schema per document,
  you get near-duplicates: `receipt`, `receipts`, `store_receipt`. So the
  classifier is **grounded in the registry** — it sees existing types and must
  justify proposing a new one.
- **Classification ≠ extraction.** "What kind of document is this?" (a label)
  and "pull these fields out" (structured data) are different tasks. Fusing them
  makes the model hedge and yields inconsistent schemas. Hence two phases (3.4).

### 3.4 Two-phase pipeline: classify, then extract

**Decision:**
- **Phase 1 — classify.** The model sees the registry (type names, descriptions,
  fields) and returns a `Decision`: match an existing type, or propose a new one,
  **with a confidence score and reasoning**.
- **Phase 2 — extract.** Using the chosen type's schema, the model fills the
  fields (schema-forced).

**Why the split:**
- Each call has one job, so each is more accurate.
- The confidence score from Phase 1 becomes the control signal for the
  human-in-the-loop gate (3.5).
- The registry passed into Phase 1 is what keeps the model from hallucinating a
  match — it can only match types that actually exist.

**Flow:** `upload → classify → (confirm if new / low-confidence) → extract → store → query`.

### 3.5 New types are gated by confidence + human confirmation

**Decision:** Auto-proceed only when the model matches an **existing** type with
confidence ≥ `0.6`. Otherwise (new type, or low-confidence match) the UI shows
the proposed schema and requires an explicit click before anything is created.

**Why:** Creating a type is a **schema change** — it adds a table/view and shapes
all future data. That is effectively irreversible and the main source of sprawl.
Gating it is the operational-safety equivalent of "confirm before dropping a
table." Cheap, reversible actions (extracting into a known type) run freely;
schema-shaping actions ask first.

**Threshold rationale:** `0.6` is a deliberate, tunable midpoint — low enough to
auto-handle confident repeat types, high enough that anything genuinely unsure
routes to a human. It is a product knob, not a magic constant.

### 3.6 Storage: JSON rows + per-type SQL views (not table-per-type columns)

**Decision:** Store every extraction as a JSON payload in one `documents` table,
tagged with its type. For each type, generate a **SQL view** that projects its
JSON fields as real columns (`view_<type>`).

**Why this shape:**
- **Queryable** is preserved: `SELECT * FROM view_receipt WHERE total > 40`
  reads like a real table because, to the query engine, it is one.
- **No destructive migrations.** If a type gains a field later, we regenerate a
  view — we never `ALTER TABLE` a column into existing rows. Old rows simply
  return `null` for the new field.
- **One storage path for all types** keeps `insert` trivial and avoids dynamic
  DDL on the hot path.

**Alternative considered — a real table per type with typed columns.** Cleaner
columns, but every schema change becomes a migration, and creating tables on the
fly is riskier. The view approach gets ~all the query ergonomics with far less
operational danger.

**Edge case handled:** view/type names are **slugified** deterministically
(`"Store Receipt"` → `store_receipt`) so casing/spacing variants collide into one
identifier instead of spawning duplicates, and so identifiers are always
SQL-safe.

### 3.7 A small, closed field-type vocabulary

**Decision:** Fields may only be `string`, `number`, `integer`, `boolean`,
`date` (ISO string), or `list` (list of strings).

**Why:** Both the LLM and the SQLite view layer must map every type
unambiguously. A closed set means there is never a field type we can't store or
can't project into a view. It also keeps the model's proposed schemas simple and
comparable.

**Trade-off / known limit:** Structured children — e.g. receipt line items with
a per-item `amount` — are **not** modeled in v1. A `list` holds strings only.
Supporting nested objects would need either nested schemas (harder to force and
to view) or a child table with a foreign key. Deferred deliberately (see §6).

### 3.8 SQLite over a server database

**Decision:** SQLite.

**Why:** Built into Python, zero setup, transactional, and gives us SQL — which
*is* the "queryable" deliverable — for free. For a single-user local/first
deployment it is the correct amount of database. Postgres is a clean future swap
if concurrency or scale demands it.

### 3.9 Streamlit for the UI

**Decision:** Streamlit.

**Why:** File upload, tables, buttons, and a query box with almost no frontend
code. It lets the whole left-to-right journey be demoed and driven by a
non-developer. The cost is less control over UX and a websocket-based runtime
(which shaped the deployment, see §5).

---

## 4. Data model

```
doc_types                     documents                    view_<type> (generated)
---------                     ---------                    -----------------------
name  (slug, PK)              id (PK)                       id
description                   doc_type  ─── references ──▶  source_name
fields_json (schema)          source_name                  extracted_at
created_at                    extracted_at                 <one column per field,
                              data_json  (the payload)       via json_extract>
```

- `doc_types` is the **source of truth** the classifier is grounded in.
- `documents` is uniform, append-only storage.
- `view_<type>` is derived and disposable — safe to drop and rebuild anytime.

---

## 5. Deployment decisions

Target: a Hostinger VPS (Ubuntu), served at `https://ashughildiyal.cloud`.

| Concern | Decision | Why |
| ------- | -------- | --- |
| Process management | **systemd** service (`u2q.service`) | Auto-restart on crash, starts on boot, standard logging via `journalctl` |
| Reverse proxy | **nginx** → `127.0.0.1:8501` | App never binds public ports directly; nginx terminates TLS and handles the domain |
| Websockets | nginx `Upgrade`/`Connection` headers + long `proxy_read_timeout` | Streamlit is websocket-driven; without this the UI silently fails to update |
| TLS | **Let's Encrypt** via certbot, HTTP→HTTPS redirect | Free, auto-renewing certs; redirect makes HTTPS the only surface |
| Secrets | `.env` on the server, `git`-ignored, `umask 077` | API key never enters the repo, chat, or shell history |

**Deployment complexities actually hit (and how they were resolved):**

- **Broken apt mirror.** A third-party mirror (`mirror.cse.iitk.ac.in`) 404'd
  and blocked `apt update`. Resolved by disabling that source file; the official
  `archive.ubuntu.com` was already configured.
- **SSH sessions dying between steps.** Long gaps (the operator stepping away,
  laptop sleeping) killed interactive sessions mid-flow. Resolved by collapsing
  the entire deploy into **one non-interactive script** that reads both secrets
  up front via hidden prompts, then runs to completion — so session lifetime no
  longer matters.
- **Secrets in the process list.** The private-repo clone used a `git`
  credential helper that reads the PAT from an env var, keeping it out of the
  clone URL, shell history, and `ps` output.
- **The IPv6 certbot failure — the subtle one.** The domain had an **AAAA
  (IPv6)** record, so Let's Encrypt validated over IPv6. But the nginx site only
  had `listen 80;` (IPv4). IPv6 challenge requests fell through to the default
  server and returned **404**, so issuance failed. Fix: add `listen [::]:80;` to
  the site so it answers on both stacks, then re-run certbot. **Lesson:** if a
  domain has an AAAA record, every public-facing server block must listen on
  IPv6 too, or ACME (and real IPv6 users) hit the wrong vhost.

---

## 6. Edge cases, failure modes, and how they're handled

| Case | Handling | Status |
| ---- | -------- | ------ |
| Model proposes a near-duplicate type | Registry grounding + slug collision + confidence gate | Mitigated, not eliminated |
| Model matches a type it shouldn't | Low-confidence matches require confirmation | Mitigated |
| Field the model can't find | All fields optional → returns `null` instead of inventing | Handled |
| Type gains a field later | JSON storage + regenerated view; old rows read `null` | Handled (no re-extraction yet) |
| Wrong value in the right field (misread) | — | **Open:** no value validation yet |
| Malicious SQL in the query box | — | **Open:** raw `WHERE` is trusted (single-user, local) |
| Casing/spacing variants of a type name | Deterministic slugging | Handled |
| Nested/structured children (line items) | — | **Out of scope for v1** |
| Model/API id drift | `MODEL` constant, confirmable via `list_models.py` | Handled operationally |

---

## 7. Security posture

- **Secrets never in the repo or in git history** — `.env` is git-ignored;
  storage DBs (`*.db`) are ignored too.
- **On the server**, the key lives only in `/opt/.../.env` with tight perms.
- **Known weak point:** the query UI passes a user-supplied SQL `WHERE` clause
  straight to SQLite. This is acceptable for a **single-user, local/trusted**
  deployment but is an injection surface and **must not** be exposed to
  untrusted users. The intended fix is a natural-language → validated-SQL layer,
  or a parameterized query builder that never lets raw SQL through.

---

## 8. Known limitations & risks

- **Extraction correctness is unvalidated** beyond field *types*. Dates aren't
  parsed, numbers aren't range-checked. A confidently wrong total is stored as-is.
- **Type sprawl is reduced, not solved.** A human can still confirm a bad new
  type. A registry **merge/rename** tool is needed to curate over time.
- **No schema evolution flow.** Adding a field doesn't re-extract historical
  documents; it only affects new ones.
- **Scalar + string-list fields only.** Rich nested structures need more design.
- **Model non-determinism.** Same document can classify slightly differently run
  to run; the confidence gate absorbs some of this but not all.

---

## 9. Next steps

1. **Value validation** — parse dates, enforce numeric ranges, flag low-confidence
   *field-level* extractions (not just type-level).
2. **Registry curation** — merge/rename/deprecate types; view the type graph.
3. **Safe querying** — replace the raw `WHERE` box with natural-language → SQL or
   a constrained query builder.
4. **Nested types** — model structured children (line items) via child tables.
5. **Schema evolution** — offer re-extraction when a type gains fields.
6. **Multi-user hardening** — auth, per-user data isolation, and moving off raw
   SQL before exposing publicly.

---

## 10. Concept glossary

- **Unstructured data** — information with no consistent machine-readable
  position (a photo, an email, a paragraph).
- **Semi-structured data** — a recognizable pattern with variable layout
  (receipts, invoices, forms).
- **Structured data** — values in labeled columns of a known type.
- **Schema** — the chosen set of labeled fields and their types.
- **Queryable** — stored so a computer can filter/sort/aggregate and answer
  questions instantly.
- **Registry** — the catalog of known document types; the classifier's source of
  truth.
- **Schema-forcing** — constraining the model's output to a fixed schema so the
  result is shaped like the destination table.
