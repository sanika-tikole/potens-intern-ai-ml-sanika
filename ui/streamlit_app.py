from __future__ import annotations

from typing import Any

import requests
import streamlit as st


try:
    API_BASE_URL = st.secrets["POLICYLENS_API_BASE_URL"]
except Exception:
    st.error("Missing Streamlit secret: POLICYLENS_API_BASE_URL. Add it to .streamlit/secrets.toml.")
    st.stop()

st.set_page_config(page_title="PolicyLens", page_icon="PL", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #eef7ff 0%, #e6f1fb 42%, #dbeaf7 100%);
        color: #000000;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 1480px;
    }
    .hero {
        background: linear-gradient(135deg, rgba(184, 217, 243, 0.98), rgba(165, 203, 233, 0.98));
        color: #000000;
        border-radius: 24px;
        padding: 1.6rem 1.8rem;
        box-shadow: 0 18px 50px rgba(72, 95, 121, 0.10);
        margin-bottom: 1.25rem;
        border: 1px solid rgba(74, 105, 138, 0.14);
    }
    .hero h1 {
        margin: 0;
        font-size: 2.2rem;
        color: #000000;
    }
    .hero p {
        margin: 0.35rem 0 0 0;
        opacity: 1;
        color: #000000;
    }
    .panel {
        background: linear-gradient(180deg, rgba(199, 223, 242, 0.98), rgba(182, 212, 235, 0.98));
        border: 1px solid rgba(74, 105, 138, 0.12);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 28px rgba(72, 95, 121, 0.05);
        margin-bottom: 0.8rem;
        color: #000000;
    }
    .citation-card {
        background: linear-gradient(180deg, rgba(207, 228, 244, 0.98), rgba(191, 218, 237, 0.98));
        border: 1px solid rgba(74, 105, 138, 0.12);
        border-radius: 16px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 8px 20px rgba(72, 95, 121, 0.04);
        color: #000000;
    }
    .citation-meta {
        font-size: 0.88rem;
        color: #000000;
        margin-bottom: 0.35rem;
    }
    .status-chip {
        display: inline-block;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        background: linear-gradient(180deg, rgba(207, 228, 244, 0.96), rgba(191, 218, 237, 0.96));
        color: #000000;
        font-size: 0.82rem;
        font-weight: 600;
        border: 1px solid rgba(74, 105, 138, 0.18);
    }
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #000000;
    }
    .stButton > button {
        background: linear-gradient(180deg, rgba(150, 195, 232, 0.98), rgba(121, 176, 222, 0.98)) !important;
        color: #000000 !important;
        border: 1px solid rgba(66, 113, 155, 0.34) !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background: linear-gradient(180deg, rgba(132, 182, 224, 0.98), rgba(106, 166, 215, 0.98)) !important;
        color: #000000 !important;
        border-color: rgba(66, 113, 155, 0.42) !important;
    }
    .stButton > button:focus,
    .stButton > button:active {
        background: linear-gradient(180deg, rgba(132, 182, 224, 0.98), rgba(106, 166, 215, 0.98)) !important;
        color: #000000 !important;
    }
    .stTextInput input,
    .stTextArea textarea {
        background-color: rgba(235, 244, 252, 0.98) !important;
        color: #000000 !important;
        caret-color: #000000 !important;
    }
    .stTextInput div[data-baseweb="input"],
    .stTextArea div[data-baseweb="base-input"],
    .stTextInput [data-baseweb="base-input"],
    .stTextArea [data-baseweb="base-input"] {
        background-color: rgba(235, 244, 252, 0.98) !important;
        color: #000000 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(211, 231, 246, 0.90) !important;
        border: 1px solid rgba(74, 105, 138, 0.12) !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #000000 !important;
    }
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: rgba(0, 0, 0, 0.45) !important;
        opacity: 1 !important;
    }
    .stTextInput [data-baseweb="input"] input,
    .stTextArea [data-baseweb="base-input"] textarea {
        background-color: transparent !important;
        color: #000000 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _call_api(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=90)
    response.raise_for_status()
    return response.json()


def _render_citations(citations: list[dict[str, Any]], empty_message: str) -> None:
    if not citations:
        st.info(empty_message)
        return

    st.markdown("### Citations")
    for citation in citations:
        page = citation.get("page")
        page_label = f"page {page}" if page is not None else "page n/a"
        st.markdown(
            f"""
            <div class="citation-card">
              <div class="citation-meta"><strong>{citation.get('source_file', 'unknown')}</strong> · {page_label} · {citation.get('chunk_id', 'unknown')}</div>
              <div>{citation.get('snippet', '')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.markdown(
    """
    <div class="hero">
      <h1>PolicyLens</h1>
      <p>Multilingual policy Q&A with grounded citations and contradiction checking.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([3, 1])
with left:
    st.caption(f"Backend: {API_BASE_URL}")
with right:
    if st.button("Check Backend Status", use_container_width=True):
        try:
            with st.spinner("Checking backend..."):
                health = requests.get(f"{API_BASE_URL}/health", timeout=15)
                health.raise_for_status()
                health_payload = health.json()
            st.success(f"Backend is healthy: {health_payload.get('status', 'ok')}")
        except requests.RequestException:
            st.error(f"Backend is unavailable at {API_BASE_URL}. Check the deployed API URL and try again.")

ask_tab, contradiction_tab = st.tabs(["Ask Questions", "Contradiction Checker"])

with ask_tab:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Ask Questions")
    question = st.text_input(
        "Question",
        placeholder="Ask in English, Hindi, or Marathi",
        help="PolicyLens will ground the answer in the indexed documents.",
    )
    ask_clicked = st.button("Get Answer", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if ask_clicked:
        if not question.strip():
            st.warning("Enter a question before submitting.")
        else:
            try:
                with st.spinner("Searching documents and generating a grounded answer..."):
                    result = _call_api("/ask", {"question": question.strip()})
                st.markdown("### Answer")
                st.write(result.get("answer", ""))
                st.markdown(
                    f"<span class='status-chip'>Language: {result.get('language', 'en')}</span>",
                    unsafe_allow_html=True,
                )
                _render_citations(result.get("citations", []), "No citations were returned for this answer.")
            except requests.RequestException:
                st.error(f"Backend request failed. Make sure the API is reachable at {API_BASE_URL}.")

with contradiction_tab:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Contradiction Checker")
    col1, col2 = st.columns(2)
    with col1:
        doc1_id = st.text_input("Document 1 ID", placeholder="example_policy_a")
    with col2:
        doc2_id = st.text_input("Document 2 ID", placeholder="example_policy_b")
    topic = st.text_input("Topic", placeholder="leave policy, data retention, reimbursement, etc.")
    compare_clicked = st.button("Compare Documents", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if compare_clicked:
        if not doc1_id.strip() or not doc2_id.strip() or not topic.strip():
            st.warning("Provide both document IDs and a topic before comparing.")
        else:
            try:
                with st.spinner("Retrieving evidence and checking for contradictions..."):
                    result = _call_api(
                        "/contradict",
                        {
                            "doc1_id": doc1_id.strip(),
                            "doc2_id": doc2_id.strip(),
                            "topic": topic.strip(),
                        },
                    )

                conflict = result.get("conflict")
                if conflict is True:
                    st.error("The documents appear to conflict on this topic.")
                elif conflict is False:
                    st.success("No direct conflict was detected on this topic.")
                else:
                    st.warning("The evidence is insufficient to determine a conflict confidently.")

                st.markdown("### Reasoning")
                st.write(result.get("reasoning", ""))
                evidence = result.get("evidence", [])
                _render_citations(
                    [
                        {
                            "source_file": item.get("doc", "unknown"),
                            "page": item.get("page"),
                            "chunk_id": item.get("chunk_id", "unknown"),
                            "snippet": item.get("snippet", ""),
                        }
                        for item in evidence
                    ],
                    "No evidence chunks were returned.",
                )
            except requests.RequestException:
                st.error(f"Backend request failed. Make sure the API is reachable at {API_BASE_URL}.")
