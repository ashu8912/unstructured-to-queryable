import pandas as pd
import streamlit as st

from db import list_types, run_query, total_documents, type_counts
import ui

ui.hero("Explore", "Browse, chart and export your structured data.",
        eyebrow="Structured data")

notice = st.session_state.pop("saved_notice", None)
if notice:
    st.toast(f"Saved to {notice}", icon=":material/check_circle:")

types_ = list_types()
if not types_:
    st.info("No documents yet. Head to **Extract** to add your first one.",
            icon=":material/upload_file:")
    st.stop()

counts = type_counts()
biggest = max(counts.items(), key=lambda kv: kv[1], default=("—", 0))

c1, c2, c3 = st.columns(3)
c1.metric("Documents", total_documents(), border=True)
c2.metric("Types", len(types_), border=True)
c3.metric(f"Largest type · {biggest[0]}", f"{biggest[1]} docs", border=True)

names = [t["name"] for t in types_]
chosen = st.selectbox("Type", names,
                      index=names.index(notice) if notice in names else 0)
rows = run_query(f'SELECT * FROM "view_{chosen}" ORDER BY id DESC')
df = pd.DataFrame(rows)

with st.container(border=True):
    st.markdown(f"**{chosen}** — {len(df)} rows")
    st.dataframe(df, hide_index=True)
    st.download_button(
        "Download CSV", df.to_csv(index=False).encode(),
        file_name=f"{chosen}.csv", mime="text/csv", icon=":material/download:")

# A quick chart when there's an obvious category + number pair.
meta = {"id", "source_name", "extracted_at"}
num_cols = [c for c in df.columns if c not in meta
            and pd.api.types.is_numeric_dtype(df[c])]
cat_cols = [c for c in df.columns if c not in meta and c not in num_cols]
if num_cols and cat_cols and len(df) > 1:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        cat = c1.selectbox("Group by", cat_cols)
        val = c2.selectbox("Measure", num_cols)
        agg = df.groupby(cat, dropna=False)[val].sum().reset_index()
        st.bar_chart(agg, x=cat, y=val)
