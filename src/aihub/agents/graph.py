"""Stateful multi-agent orchestrator built with LangGraph (Module 6).

router -> {rag | sql | web | summarize | chat} -> END
Every node is a plain function over injected dependencies, so the graph is unit-testable
without any network access.
"""
import logging
import re
from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, StateGraph

from ..llm import text_of
from ..rag.chain import answer_from_docs

log = logging.getLogger(__name__)
ROUTES = ("rag", "sql", "web", "summarize", "chat")
URL_RE = re.compile(r"https?://\S+")


class AgentState(TypedDict, total=False):
    question: str
    history: list[tuple[str, str]]
    route: str
    answer: str
    sources: list
    extra: dict


def heuristic_route(question: str, has_docs: bool, has_sql: bool) -> str | None:
    if URL_RE.search(question) and re.search(r"summar|tl;?dr|what.*(about|says)", question, re.I):
        return "summarize"
    return None


def build_agent(llm, kb, sql_chat: Callable, search_fn: Callable, summarize_fn: Callable):
    """`sql_chat`: zero-arg factory returning an object with .ask(question) (lazy, DB optional)."""

    def router(state: AgentState) -> AgentState:
        q = state["question"]
        forced = heuristic_route(q, kb.has_documents(), True)
        if forced:
            return {"route": forced}
        prompt = (
            "Classify the user's message into exactly one label:\n"
            "rag = about the user's uploaded documents\n"
            "sql = about structured business data (sales, customers, orders, products, counts)\n"
            "web = needs current/public information from the internet\n"
            "chat = greetings or general knowledge\n"
            f"Documents uploaded: {kb.has_documents()}\n"
            f"Message: {q}\nAnswer with only the label."
        )
        label = text_of(llm.invoke(prompt)).lower()
        route = next((r for r in ROUTES if r in label), "chat")
        if route == "rag" and not kb.has_documents():
            route = "chat"
        log.info("route=%s", route)
        return {"route": route}

    def rag_node(state: AgentState) -> AgentState:
        docs = kb.search(state["question"])
        out = answer_from_docs(llm, state["question"], state.get("history", []), docs)
        return {"answer": out["answer"], "sources": out["sources"]}

    def sql_node(state: AgentState) -> AgentState:
        out = sql_chat().ask(state["question"])
        return {"answer": out["answer"], "extra": {"sql": out["sql"], "rows": out["rows"]}}

    def web_node(state: AgentState) -> AgentState:
        results = search_fn(state["question"])
        if not results:
            return {"answer": "The web search returned no results.", "sources": []}
        ctx = "\n".join(f"- {r['title']} ({r['url']}): {r['snippet']}" for r in results)
        msg = llm.invoke(
            f"Answer using these search results; mention sources by title.\n{ctx}\n\n"
            f"Question: {state['question']}"
        )
        return {"answer": text_of(msg), "sources": [{"source": r["url"]} for r in results]}

    def summarize_node(state: AgentState) -> AgentState:
        url = URL_RE.search(state["question"]).group(0).rstrip(").,")
        out = summarize_fn(url)
        return {"answer": out["summary"], "sources": [{"source": url}]}

    def chat_node(state: AgentState) -> AgentState:
        msgs = [("system", "You are AIHub, a helpful, concise assistant.")]
        msgs += state.get("history", []) + [("human", state["question"])]
        return {"answer": text_of(llm.invoke(msgs)), "sources": []}

    g = StateGraph(AgentState)
    g.add_node("router", router)
    for name, fn in [("rag", rag_node), ("sql", sql_node), ("web", web_node),
                     ("summarize", summarize_node), ("chat", chat_node)]:
        g.add_node(name, fn)
        g.add_edge(name, END)
    g.set_entry_point("router")
    g.add_conditional_edges("router", lambda s: s["route"], {r: r for r in ROUTES})
    return g.compile()
