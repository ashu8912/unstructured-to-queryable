import pandas as pd
import streamlit as st

from db import delete_type, list_types, type_counts
import ui

ui.hero("Document types",
        "The registry of everything the system has learned to recognize.",
        eyebrow="Registry")

types_ = list_types()
if not types_:
    st.info("No types yet. They're created as you extract documents.",
            icon=":material/schema:")
    st.stop()

counts = type_counts()
overview = pd.DataFrame([
    {"type": t["name"],
     "documents": counts.get(t["name"], 0),
     "fields": ", ".join(f.name for f in t["fields"]),
     "description": t["description"]}
    for t in types_
])
st.dataframe(overview, hide_index=True)

with st.container(border=True):
    st.markdown("**Manage a type**")
    chosen = st.selectbox("Type", [t["name"] for t in types_])
    n = counts.get(chosen, 0)
    st.caption(f"Deleting removes the type and its {n} document(s). This can't be undone.")
    with st.popover("Delete type", icon=":material/delete:"):
        st.warning(f"Permanently delete **{chosen}** and {n} document(s)?")
        if st.button("Yes, delete", type="primary", icon=":material/delete_forever:"):
            delete_type(chosen)
            st.toast(f"Deleted {chosen}", icon=":material/check_circle:")
            st.rerun()
