
from aihub.agents.graph import build_agent
from tests.conftest import FakeKB, FakeLLM


def make(route_reply, has_docs=False):
    return build_agent(
        FakeLLM(route_reply), FakeKB(has_docs),
        sql_chat=lambda: type("S", (), {"ask": lambda self, q: {"answer": "42", "sql": "SELECT 1",
                                                                "rows": [[42]]}})(),
        search_fn=lambda q: [{"title": "T", "url": "http://x", "snippet": "s"}],
        summarize_fn=lambda url: {"summary": f"sum of {url}"},
    )


def run(agent, q):
    return agent.invoke({"question": q, "history": []})


def test_url_summary_route_is_heuristic():
    out = run(make("chat"), "Please summarize https://example.com/post")
    assert out["route"] == "summarize" and "sum of https://example.com/post" in out["answer"]


def test_sql_route():
    out = run(make("sql"), "How many orders?")
    assert out["route"] == "sql" and out["answer"] == "42"


def test_rag_falls_back_to_chat_without_docs():
    assert run(make("rag", has_docs=False), "what does my pdf say")["route"] == "chat"


def test_unknown_label_defaults_to_chat():
    assert run(make("banana"), "hello")["route"] == "chat"
