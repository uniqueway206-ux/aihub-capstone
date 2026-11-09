"""Streamlit front end (Module 1: rapid prototyping). Talks to the Flask API over HTTP."""
import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

st.set_page_config(page_title="AIHub", page_icon="🤖", layout="wide")


def call(method: str, path: str, **kw):
    try:
        r = requests.request(method, f"{API_URL}{path}", headers=HEADERS, timeout=120, **kw)
    except requests.RequestException as e:
        st.error(f"API unreachable: {e}")
        return None
    if not r.ok:
        st.error(r.json().get("error", f"HTTP {r.status_code}") if r.content else r.status_code)
        return None
    return r.json()


if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []

with st.sidebar:
    st.title("🤖 AIHub")
    st.caption("Chat • RAG • SQL • Web • Summaries")
    st.subheader("Documents")
    up = st.file_uploader("Upload PDF", type="pdf")
    if up and st.button("Index PDF"):
        with st.spinner("Indexing..."):
            res = call("POST", "/api/documents", files={"file": (up.name, up, "application/pdf")})
        if res:
            st.success(f"Indexed {res['file']} ({res['chunks']} chunks)")
    docs = (call("GET", "/api/documents") or {}).get("documents", {})
    for name, n in docs.items():
        st.write(f"📄 {name} — {n} chunks")
    if docs and st.button("Clear all documents"):
        call("DELETE", "/api/documents")
        st.rerun()
    if st.button("New conversation"):
        call("DELETE", f"/api/chat/{st.session_state.session_id}")
        st.session_state.messages = []
        st.rerun()

chat_tab, sum_tab, sql_tab = st.tabs(["💬 Assistant", "🔗 Summarizer", "🗄️ SQL"])

with chat_tab:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("meta"):
                st.caption(m["meta"])
    if prompt := st.chat_input("Ask about your PDFs, data, the web, or paste a URL to summarise"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                res = call("POST", "/api/chat",
                           json={"session_id": st.session_state.session_id, "message": prompt})
            if res:
                srcs = ", ".join(
                    f"{s.get('source')}" + (f" p.{s['page']}" if s.get("page") else "")
                    for s in res["sources"]
                )
                meta = f"route: {res['route']}" + (f" • sources: {srcs}" if srcs else "")
                st.markdown(res["answer"])
                st.caption(meta)
                if res["details"].get("sql"):
                    st.code(res["details"]["sql"], language="sql")
                st.session_state.messages.append(
                    {"role": "assistant", "content": res["answer"], "meta": meta})

with sum_tab:
    url = st.text_input("Web page or YouTube URL")
    if st.button("Summarise") and url:
        with st.spinner("Fetching and summarising..."):
            res = call("POST", "/api/summarize", json={"url": url})
        if res:
            st.caption(f"Type: {res['type']}")
            st.markdown(res["summary"])

with sql_tab:
    q = st.text_input("Ask your database", placeholder="Top 3 customers by total spend?")
    if st.button("Run query") and q:
        with st.spinner("Generating SQL..."):
            res = call("POST", "/api/sql", json={"question": q})
        if res:
            st.markdown(res["answer"])
            st.code(res["sql"], language="sql")
            st.dataframe([dict(zip(res["columns"], r, strict=False)) for r in res["rows"]])
