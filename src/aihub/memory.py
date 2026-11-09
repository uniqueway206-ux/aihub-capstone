"""Thread-safe, bounded per-session chat memory (Module 4: chatbots with memory).

In-memory by design for a single-node deployment; swap for Redis by keeping this interface.
"""
import threading
from collections import OrderedDict


class SessionStore:
    def __init__(self, max_turns: int = 10, max_sessions: int = 1000):
        self._max_messages = max_turns * 2
        self._max_sessions = max_sessions
        self._data: OrderedDict[str, list[tuple[str, str]]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, session_id: str) -> list[tuple[str, str]]:
        with self._lock:
            return list(self._data.get(session_id, []))

    def add_turn(self, session_id: str, user: str, assistant: str) -> None:
        with self._lock:
            msgs = self._data.setdefault(session_id, [])
            msgs.extend([("human", user), ("ai", assistant)])
            del msgs[: max(0, len(msgs) - self._max_messages)]
            self._data.move_to_end(session_id)
            while len(self._data) > self._max_sessions:
                self._data.popitem(last=False)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)
