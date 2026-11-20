import sqlite3

import pytest

from aihub.agents.graph import build_agent
from aihub.errors import NotADatabaseQuestion
from aihub.tools.sql_tool import SQLChat
from tests.conftest import FakeKB, FakeLLM


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE customers(id INTEGER, city TEXT)")
    con.execute("INSERT INTO customers VALUES (1, 'Lahore')")
    con.commit()
    con.close()
    return path


def test_sql_rejects_query_without_a_real_table(db):
    chat = SQLChat(FakeLLM("SELECT 3 AS layers"), db)
    with pytest.raises(NotADatabaseQuestion):
        chat.ask("How many layers protect the SQL feature?")


def test_sql_accepts_real_table(db):
    chat = SQLChat(FakeLLM("SELECT city FROM customers"), db)
    assert chat.ask("Which city?")["rows"] == [["Lahore"]]


class Boom:
    def ask(self, q):
        raise NotADatabaseQuestion("no")


def make(has_docs):
    return build_agent(
        FakeLLM("sql"), FakeKB(has_docs), sql_chat=lambda: Boom(),
        search_fn=lambda q: [], summarize_fn=lambda u: {"summary": ""},
    )


def test_bad_sql_route_falls_back_to_rag_when_documents_exist():
    out = make(True).invoke({"question": "How many layers protect SQL?", "history": []})
    assert out["route"] == "rag"


def test_bad_sql_route_falls_back_to_chat_without_documents():
    out = make(False).invoke({"question": "How many layers protect SQL?", "history": []})
    assert out["route"] == "chat"


def test_router_prompt_lists_uploaded_documents():
    class Rec(FakeLLM):
        def invoke(self, prompt, *a, **k):
            self.prompts = getattr(self, "prompts", []) + [prompt]
            return "chat"

    llm = Rec()
    agent = build_agent(llm, FakeKB(True), sql_chat=lambda: Boom(),
                        search_fn=lambda q: [], summarize_fn=lambda u: {"summary": ""})
    agent.invoke({"question": "Which embedding model does AIHub use?", "history": []})
    assert "a.pdf" in llm.prompts[0]
