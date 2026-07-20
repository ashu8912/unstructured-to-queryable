import pandas as pd
import streamlit as st

from classify import classify_document
from extract import extract_document
from db import insert_document, list_types, get_type, register_type, type_exists
from schema import FieldSpec, slug
import ui

CONFIDENCE_THRESHOLD = 0.6

ui.hero("Extract a document",
        "Upload a file, classify it, review the fields, then save.",
        eyebrow="Document intake")


def _clear(*keys):
    for k in keys:
        st.session_state.pop(k, None)


def _field_input(f: FieldSpec, current):
    """Render an editable input for one field, preserving nulls."""
    key = f"rev_{slug(f.name)}"
    label = f.name.replace("_", " ").capitalize()
    if f.type == "boolean":
        return st.checkbox(label, value=bool(current), key=key)
    if f.type == "list":
        text = st.text_area(
            label, value="\n".join(current) if isinstance(current, list) else "",
            key=key, help="One item per line")
        return [x.strip() for x in text.splitlines() if x.strip()] or None
    raw = st.text_input(label, value="" if current is None else str(current), key=key)
    raw = raw.strip()
    if raw == "":
        return None
    if f.type in ("number", "integer"):
        try:
            return int(float(raw)) if f.type == "integer" else float(raw)
        except ValueError:
            st.caption(f":red[“{raw}” isn't a valid {f.type}]")
            return None
    return raw


# --- 1. upload + classify -------------------------------------------------
up = st.file_uploader("Document", type=["pdf", "png", "jpg", "jpeg"],
                      label_visibility="collapsed")

if up and st.button("Analyze document", type="primary", icon=":material/search:"):
    _clear("extracted", "ex_name", "ex_fields", "ex_known", "ex_desc")
    try:
        with st.spinner("Classifying…"):
            decision = classify_document(
                up.getvalue(), up.type or "application/pdf", list_types())
        st.session_state.decision = decision.model_dump()
        st.session_state.file_bytes = up.getvalue()
        st.session_state.mime = up.type or "application/pdf"
        st.session_state.source = up.name
    except Exception as e:
        ui.error_box(e, "Couldn't classify the document")

# --- 2. show classification + extract -------------------------------------
decision = st.session_state.get("decision")
if decision:
    name = slug(decision["type_name"])
    known = type_exists(name)
    fields = (get_type(name)["fields"] if known
              else [FieldSpec(**f) for f in decision["fields"]])
    confident = decision["confidence"] >= CONFIDENCE_THRESHOLD

    with st.container(border=True):
        head = st.container(horizontal=True)
        with head:
            st.metric("Confidence", f"{decision['confidence'] * 100:.0f}%")
            with st.container():
                st.markdown(f"#### {name}")
                if known and confident:
                    st.badge("Known type", icon=":material/check:", color="green")
                elif known:
                    st.badge("Low-confidence match", icon=":material/help:", color="orange")
                else:
                    st.badge("New type", icon=":material/add:", color="violet")
        if decision.get("reasoning"):
            st.caption(decision["reasoning"])
        if not known:
            st.caption("This type doesn't exist yet — it will be created when you save.")
            st.dataframe(pd.DataFrame([f.model_dump() for f in fields]),
                         hide_index=True)

    preview, action = st.columns([3, 2])
    with preview:
        if st.session_state.mime.startswith("image"):
            st.image(st.session_state.file_bytes, caption=st.session_state.source)
        else:
            st.caption(":material/picture_as_pdf: PDF — preview not shown")
    with action:
        st.markdown(f"**Source:** {st.session_state.source}")
        st.markdown(f"**Fields:** {len(fields)}")

    left, mid, right = st.columns([1, 1, 1])
    with mid:
        if st.button("Extract fields", type="primary", icon=":material/bolt:",
                     width="stretch"):
            try:
                with st.spinner("Extracting…"):
                    data = extract_document(
                        st.session_state.file_bytes, st.session_state.mime,
                        name, fields)
                st.session_state.extracted = data
                st.session_state.ex_name = name
                st.session_state.ex_fields = [f.model_dump() for f in fields]
                st.session_state.ex_known = known
                st.session_state.ex_desc = decision["description"]
            except Exception as e:
                ui.error_box(e, "Couldn't extract the fields")

# --- 3. review + save -----------------------------------------------------
if st.session_state.get("extracted") is not None:
    st.subheader("Review & edit")
    st.caption("The model fills these in — correct anything before saving.")
    fields = [FieldSpec(**f) for f in st.session_state.ex_fields]
    extracted = st.session_state.extracted

    with st.form("review", border=True):
        edited = {}
        cols = st.columns(2)
        for i, f in enumerate(fields):
            with cols[i % 2]:
                edited[slug(f.name)] = _field_input(f, extracted.get(slug(f.name)))
        saved = st.form_submit_button("Save", type="primary", icon=":material/save:")

    if saved:
        saved_name = st.session_state.ex_name
        if not st.session_state.ex_known:
            register_type(saved_name, st.session_state.ex_desc, fields)
        insert_document(saved_name, st.session_state.source, edited)
        _clear("decision", "extracted", "ex_name", "ex_fields", "ex_known", "ex_desc",
               "file_bytes", "mime", "source")
        st.session_state.saved_notice = saved_name
        st.switch_page("app_pages/explore.py")
