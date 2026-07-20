import pandas as pd
import streamlit as st

from ask import text_to_sql
from db import get_type, list_types, run_query_readonly
import ui

ui.hero("Ask your data",
        "Ask in plain English — it becomes a read-only SQL query you can inspect.",
        eyebrow="Query")

types_ = list_types()
if not types_:
    st.info("No data yet. Add documents in **Extract** first.",
            icon=":material/upload_file:")
    st.stop()

chosen = st.selectbox("Type", [t["name"] for t in types_])
question = st.text_input(
    "Question", placeholder="e.g. total amount by store, or count of docs this month")

if st.button("Ask", type="primary", icon=":material/send:") and question:
    t = get_type(chosen)
    try:
        with st.spinner("Translating to SQL…"):
            sql = text_to_sql(question, chosen, t["fields"])
    except ValueError as e:
        st.warning(f"Couldn't build a safe query: {e}", icon=":material/shield:")
        st.stop()
    except Exception as e:
        ui.error_box(e, "Couldn't reach the AI service")
        st.stop()

    with st.expander("Generated SQL", icon=":material/code:"):
        st.code(sql, language="sql")

    try:
        df = pd.DataFrame(run_query_readonly(sql))
    except Exception as e:
        st.error(f"Query failed: {e}")
        st.stop()

    if df.empty:
        st.caption("No rows matched.")
    else:
        st.dataframe(df, hide_index=True)
        # Auto-chart a simple 2-column category→number result.
        if df.shape[1] == 2:
            x, y = df.columns
            if pd.api.types.is_numeric_dtype(df[y]) and not pd.api.types.is_numeric_dtype(df[x]):
                st.bar_chart(df, x=x, y=y)
