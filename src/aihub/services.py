"""Lazy service container: heavy objects (LLM, embeddings, FAISS) are built on first use,
so /health and unit tests never need API keys or model downloads."""
import threading
from functools import cached_property

from .agents.graph import build_agent
from .config import Settings
from .llm import build_llm
from .memory import SessionStore
from .rag.store import KnowledgeBase
from .tools.sql_tool import SQLChat
from .tools.web import summarize_url, web_search


class Services:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions = SessionStore(max_turns=settings.max_history_turns)
        self._lock = threading.Lock()

    @cached_property
    def llm(self):
        return build_llm(self.settings)

    @cached_property
    def kb(self) -> KnowledgeBase:
        return KnowledgeBase(self.settings)

    def sql(self) -> SQLChat:
        with self._lock:
            if not hasattr(self, "_sql"):
                self._sql = SQLChat(self.llm, self.settings.sql_database_path,
                                    self.settings.sql_row_limit)
            return self._sql

    @cached_property
    def agent(self):
        return build_agent(
            self.llm, self.kb, self.sql, web_search, lambda url: summarize_url(self.llm, url)
        )

    def chat(self, session_id: str, message: str) -> dict:
        history = self.sessions.get(session_id)
        state = self.agent.invoke({"question": message, "history": history})
        self.sessions.add_turn(session_id, message, state["answer"])
        return {
            "answer": state["answer"],
            "route": state.get("route"),
            "sources": state.get("sources", []),
            "details": state.get("extra", {}),
        }
