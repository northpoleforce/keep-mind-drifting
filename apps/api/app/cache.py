from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Generic, TypeVar

from .models import ContextItem

V = TypeVar("V")


class TTLDict(Generic[V]):
    """Dict with per-key TTL expiry. Not thread-safe — intended for single-worker use."""

    def __init__(self, ttl_seconds: float = 3600) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, tuple[float, V]] = {}

    def get(self, key: str, default: V | None = None) -> V | None:
        entry = self._data.get(key)
        if entry is None:
            return default
        ts, val = entry
        if time.monotonic() - ts > self._ttl:
            del self._data[key]
            return default
        return val

    def __setitem__(self, key: str, value: V) -> None:
        self._data[key] = (time.monotonic(), value)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


class SessionCache:
    def __init__(self, max_items: int = 20) -> None:
        self.max_items = max_items
        self._store: dict[str, deque[ContextItem]] = defaultdict(lambda: deque(maxlen=self.max_items))

    def add(self, session_id: str, text: str) -> None:
        self._store[session_id].append(ContextItem(text=text, score=1.0, source="cache"))

    def query(self, session_id: str, limit: int = 5) -> list[ContextItem]:
        items = list(self._store.get(session_id, []))
        return items[-limit:]
