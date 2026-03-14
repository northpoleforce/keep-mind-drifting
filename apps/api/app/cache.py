from collections import defaultdict, deque

from .models import ContextItem


class SessionCache:
    def __init__(self, max_items: int = 20) -> None:
        self.max_items = max_items
        self._store: dict[str, deque[ContextItem]] = defaultdict(lambda: deque(maxlen=self.max_items))

    def add(self, session_id: str, text: str) -> None:
        self._store[session_id].append(ContextItem(text=text, score=1.0, source="cache"))

    def query(self, session_id: str, limit: int = 5) -> list[ContextItem]:
        items = list(self._store.get(session_id, []))
        return items[-limit:]
