import pytest

from aihub.api.app import create_app
from aihub.config import Settings
from aihub.memory import SessionStore


class FakeLLM:
    def __init__(self, reply="chat"):
        self.reply = reply

    def invoke(self, *_a, **_k):
        return self.reply


class FakeKB:
    def __init__(self, has=False):
        self.has = has

    def has_documents(self):
        return self.has

    def search(self, q, k=None):
        return []

    def documents(self):
        return {"a.pdf": 3}

    def clear(self):
        self.has = False


class FakeServices:
    def __init__(self):
        self.sessions = SessionStore()
        self.kb = FakeKB()
        self.llm = FakeLLM()

    def chat(self, session_id, message):
        self.sessions.add_turn(session_id, message, "hi")
        return {"answer": "hi", "route": "chat", "sources": [], "details": {}}


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path, sql_database_path=tmp_path / "x.db", rate_limit="1000/minute"
    )


@pytest.fixture
def client(settings):
    return create_app(settings, FakeServices()).test_client()
