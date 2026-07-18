import pandas as pd
import streamlit as st

from classify import classify_document
from db import (init_db, insert_document, list_types, get_type,
                register_type, run_query, type_exists)
from extract import extract_document
from schema import slug

CONFIDENCE_THRESHOLD = 0.6

init_db()
st.title("Unstructured → queryable")
st.caption("Upload any document. It gets classified into a type, extracted "
           "against that type's schema, and stored where you can query it.")

# --- upload + classify ----------------------------------------------------
up = st.file_uploader("Upload a document", type=["pdf", "png", "jpg", "jpeg"])

if up and st.button("Analyze"):
    with st.spinner("Classifying…"):
        decision = classify_document(
            up.getvalue(), up.type or "application/pdf", list_types())
    st.session_state.decision = decision.model_dump()
    st.session_state.file_bytes = up.getvalue()
    st.session_state.mime = up.type or "application/pdf"
    st.session_state.source = up.name

# --- act on the classification --------------------------------------------
decision = st.session_state.get("decision")
if decision:
    name = slug(decision["type_name"])
    known = type_exists(name)
    confident = decision["confidence"] >= CONFIDENCE_THRESHOLD
    auto = decision["match"] == "existing" and known and confident

    st.subheader("Classification")
    st.write(f"**Type:** `{name}`  ·  **match:** {decision['match']}  ·  "
             f"**confidence:** {decision['confidence']:.2f}")
    if decision.get("reasoning"):
        st.caption(decision["reasoning"])

    def _run(type_name: str, fields):
        data = extract_document(
            st.session_state.file_bytes, st.session_state.mime, type_name, fields)
        insert_document(type_name, st.session_state.source, data)
        st.json(data)
        st.success(f"Saved to `{type_name}`.")
        st.session_state.pop("decision", None)

    if auto:
        t = get_type(name)
        with st.spinner(f"Extracting as {name}…"):
            _run(name, t["fields"])
    else:
        # New type, or a low-confidence / unknown match — require confirmation.
        if not known:
            st.info("No existing type fits. Proposed new type:")
            st.write(f"**{name}** — {decision['description']}")
            st.dataframe(pd.DataFrame(decision["fields"]))
            if st.button("Create type and extract"):
                from schema import FieldSpec
                fields = [FieldSpec(**f) for f in decision["fields"]]
                register_type(name, decision["description"], fields)
                with st.spinner("Extracting…"):
                    _run(name, fields)
        else:
            st.warning("Low-confidence match to an existing type. Confirm to proceed.")
            if st.button(f"Extract as {name}"):
                t = get_type(name)
                with st.spinner("Extracting…"):
                    _run(name, t["fields"])

# --- registry -------------------------------------------------------------
st.header("Document types")
types_ = list_types()
if types_:
    st.dataframe(pd.DataFrame(
        [{"type": t["name"], "description": t["description"],
          "fields": ", ".join(f.name for f in t["fields"])} for t in types_]))
else:
    st.caption("No types yet — upload a document to create the first one.")

# --- browse + query -------------------------------------------------------
if types_:
    st.header("Browse & query")
    chosen = st.selectbox("Type", [t["name"] for t in types_])
    st.dataframe(pd.DataFrame(
        run_query(f'SELECT * FROM "view_{chosen}" ORDER BY id DESC')))

    st.subheader("Ask a question")
    where = st.text_input("Filter (SQL WHERE clause)", "1=1")
    if st.button("Run query"):
        try:
            st.dataframe(pd.DataFrame(
                run_query(f'SELECT * FROM "view_{chosen}" WHERE {where}')))
        except Exception as e:
            st.error(e)