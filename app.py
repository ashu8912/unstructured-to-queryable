import streamlit as st
import pandas as pd
from extract import extract_receipt
from db import init_db, insert_receipt, run_query

init_db()
st.title("Receipt → structured data")

up = st.file_uploader("Upload a receipt", type=["pdf", "png", "jpg", "jpeg"])
if up and st.button("Extract"):
    with st.spinner("Extracting…"):
        r = extract_receipt(up.getvalue(), up.type or "application/pdf")
    st.json(r.model_dump())
    insert_receipt(r)
    st.success("Saved.")

st.header("Your receipts")
rows = run_query("SELECT id, store, date, total, currency FROM receipts ORDER BY id DESC")
if rows:
    st.dataframe(pd.DataFrame(rows))

st.header("Ask a question")
where = st.text_input("Filter (SQL WHERE clause)", "total > 40")
if st.button("Run query"):
    try:
        st.dataframe(pd.DataFrame(
            run_query(f"SELECT store, date, total FROM receipts WHERE {where}")))
    except Exception as e:
        st.error(e)