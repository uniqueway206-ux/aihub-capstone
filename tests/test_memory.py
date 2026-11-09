from aihub.memory import SessionStore


def test_history_is_bounded():
    s = SessionStore(max_turns=2)
    for i in range(5):
        s.add_turn("a", f"q{i}", f"a{i}")
    h = s.get("a")
    assert len(h) == 4 and h[0] == ("human", "q3")


def test_clear_and_isolation():
    s = SessionStore()
    s.add_turn("a", "q", "r")
    assert s.get("b") == []
    s.clear("a")
    assert s.get("a") == []
