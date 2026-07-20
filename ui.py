"""Zamp-style presentation helpers.

The user explicitly asked for a Zamp-like look, so a small, targeted CSS layer
is used on top of the theme in `.streamlit/config.toml`:
- uppercase, letter-spaced "eyebrow" labels
- a dark accent bar beside each page's hero
- pill buttons and softened cards
"""

import streamlit as st

_CSS = """
<style>
:root { --zamp-ink:#111114; --zamp-muted:#6B675E; --zamp-faint:#8F8B80; }

/* Hero block with the signature accent bar */
.zamp-hero { border-left: 3px solid var(--zamp-ink); padding-left: 1rem;
             margin: .1rem 0 1.35rem 0; }
.zamp-eyebrow { font-family: 'Space Grotesk', ui-monospace, monospace;
                text-transform: uppercase; letter-spacing: .2em; font-size: .7rem;
                font-weight: 600; color: var(--zamp-faint); margin-bottom: .45rem; }
.zamp-title { font-family: 'Space Grotesk', sans-serif; font-weight: 700;
              font-size: 2rem; line-height: 1.08; letter-spacing: -.01em;
              margin: 0 0 .3rem 0; }
.zamp-sub { color: var(--zamp-muted); font-size: 1rem; margin: 0; }

/* Buttons: black pill, subtle lift */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    font-weight: 600; letter-spacing: .01em; }

/* Cards & metrics: warm surface, hairline border */
[data-testid="stMetric"] { background: #F7F6F2; border-radius: 14px; }

/* Tighten the top padding for a denser, app-like feel */
.block-container { padding-top: 2.4rem; }
</style>
"""


def apply_style():
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str | None = None, eyebrow: str | None = None):
    apply_style()
    parts = ['<div class="zamp-hero">']
    if eyebrow:
        parts.append(f'<div class="zamp-eyebrow">{eyebrow}</div>')
    parts.append(f'<div class="zamp-title">{title}</div>')
    if subtitle:
        parts.append(f'<div class="zamp-sub">{subtitle}</div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def error_box(exc: Exception, title: str = "Something went wrong"):
    """Render an error as a calm, readable callout instead of a raw traceback.

    Uses the friendly message from ModelUnavailable when available, and tucks
    the technical detail into an expander for debugging.
    """
    from llm import ModelUnavailable

    message = exc.user_message if isinstance(exc, ModelUnavailable) else str(exc)
    st.error(message, icon=":material/error:")
    with st.expander("Technical details", icon=":material/bug_report:"):
        st.code(f"{type(exc).__name__}: {exc}", language="text")
