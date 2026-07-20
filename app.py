import streamlit as st

from db import init_db

st.set_page_config(
    page_title="Unstructured → Queryable",
    page_icon=":material/document_scanner:",
    layout="wide",
)

init_db()

with st.sidebar:
    st.markdown(
        "<div style='font-family:\"Space Grotesk\",sans-serif;font-weight:700;"
        "font-size:1.35rem;letter-spacing:-.01em;'>zamp<span style='color:#8F8B80'>"
        "/docs</span></div>"
        "<div style='text-transform:uppercase;letter-spacing:.2em;font-size:.62rem;"
        "color:#8F8B80;margin-top:.15rem;'>Document intelligence</div>",
        unsafe_allow_html=True,
    )
    st.caption("Unstructured documents → structured, queryable data.")

pages = [
    st.Page("app_pages/extract.py", title="Extract", icon=":material/upload_file:"),
    st.Page("app_pages/explore.py", title="Explore", icon=":material/table_chart:"),
    st.Page("app_pages/ask.py", title="Ask", icon=":material/forum:"),
    st.Page("app_pages/types.py", title="Types", icon=":material/schema:"),
]

st.navigation(pages).run()