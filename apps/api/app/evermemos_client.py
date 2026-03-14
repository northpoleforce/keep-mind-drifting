from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from evermemos import EverMemOS

from .config import Settings
from .memory_gateway import MemoryGateway
from .models import ContextItem, ContextQuery, MessageRecord, TopicNodeRecord


class EvermemosClient(MemoryGateway):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.memory = EverMemOS(
            api_key=settings.evermemos_api_key,
            base_url=settings.evermemos_base_url,
            timeout=settings.evermemos_timeout_seconds,
            max_retries=settings.evermemos_max_retries,
            _strict_response_validation=False,
        ).v0.memories

    async def close(self) -> None:
        return None

    async def ping(self) -> bool:
        def _ping() -> bool:
            response = self.memory.get(extra_query={"user_id": "evermind-healthcheck"})
            return response.status is None or response.status.lower() in {"success", "ok"}

        return await asyncio.to_thread(_ping)

    async def save_message(self, record: MessageRecord) -> None:
        flush = bool(record.metadata.get("flush", False))

        def _save() -> None:
            response = self.memory.add(
                message_id=record.message_id,
                create_time=self._to_rfc3339(record.timestamp),
                sender=record.channel_id,
                sender_name=self.settings.evermemos_sender_name,
                group_id=record.session_id,
                group_name=record.channel_id,
                content=record.text,
                role=record.role,
                flush=flush,
                extra_body={
                    "extend": {
                        "topic_node_id": record.topic_node_id,
                        "metadata": record.metadata,
                    }
                },
            )
            self._ensure_accepted_status(response)

        await asyncio.to_thread(_save)

    async def save_topic_node(self, record: TopicNodeRecord) -> None:
        topic_text = self._format_topic_node(record)

        def _save() -> None:
            response = self.memory.add(
                message_id=record.topic_node_id,
                create_time=self._to_rfc3339(record.timestamp),
                sender=record.channel_id,
                sender_name=self.settings.evermemos_topic_sender_name,
                group_id=record.session_id,
                group_name=record.channel_id,
                content=topic_text,
                role="system",
                flush=False,
                extra_body={
                    "extend": {
                        "record_type": "topic_node",
                        "topic_node_id": record.topic_node_id,
                        "parent_topic_node_id": record.parent_topic_node_id,
                        "topic_summary": record.topic_summary,
                        "confidence": record.confidence,
                        "metadata": record.metadata,
                    }
                },
            )
            self._ensure_accepted_status(response)

        await asyncio.to_thread(_save)

    async def query_context(self, query: ContextQuery) -> list[ContextItem]:
        def _search() -> list[ContextItem]:
            retries = max(1, self.settings.evermemos_consistency_retries)
            delay_sec = max(0, self.settings.evermemos_consistency_delay_ms) / 1000.0

            for attempt in range(retries):
                response = self.memory.search(
                    extra_query={
                        "user_id": query.channel_id,
                        "query": query.text,
                    }
                )
                memories = getattr(response.result, "memories", None) or []
                items: list[ContextItem] = []
                for memory in memories[: query.limit]:
                    text = self._extract_memory_text(memory)
                    if not text:
                        continue
                    score = float(getattr(memory, "score", 0.0) or 0.0)
                    source = str(getattr(memory, "memory_type", "evermemos"))
                    items.append(ContextItem(text=text, score=score, source=source))

                if items or attempt == retries - 1:
                    return items

                # Evermemos add may be queued; briefly wait and retry search.
                time.sleep(delay_sec)

            return []

        return await asyncio.to_thread(_search)

    async def rebuild_flow(self, channel_id: str, session_id: str) -> list[dict[str, Any]]:
        def _get() -> list[dict[str, Any]]:
            response = self.memory.get(extra_query={"user_id": channel_id})
            memories = getattr(response.result, "memories", None) or []
            nodes: list[dict[str, Any]] = []
            for memory in memories:
                if getattr(memory, "group_id", None) != session_id:
                    continue
                extend = getattr(memory, "extend", None) or {}
                if extend.get("record_type") != "topic_node":
                    continue
                nodes.append(
                    {
                        "node_id": extend.get("topic_node_id") or getattr(memory, "id", None),
                        "parent_node_id": extend.get("parent_topic_node_id"),
                        "summary": extend.get("topic_summary") or self._extract_memory_text(memory),
                        "confidence": extend.get("confidence"),
                    }
                )
            return nodes

        return await asyncio.to_thread(_get)

    def _format_topic_node(self, record: TopicNodeRecord) -> str:
        return (
            f"[Topic Node]\n"
            f"summary: {record.topic_summary}\n"
            f"parent: {record.parent_topic_node_id or 'root'}\n"
            f"confidence: {record.confidence:.2f}"
        )

    def _extract_memory_text(self, memory: Any) -> str:
        candidates = [
            getattr(memory, "episode", None),
            getattr(memory, "summary", None),
            getattr(memory, "atomic_fact", None),
            getattr(memory, "foresight", None),
            getattr(memory, "content", None),
            getattr(memory, "subject", None),
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                joined = " ".join(str(item) for item in candidate if item)
                if joined:
                    return joined
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    def _ensure_accepted_status(self, response: Any) -> None:
        status = str(getattr(response, "status", "")).strip().lower()
        message = str(getattr(response, "message", "Unknown error"))
        if status in {"success", "ok", "queued", "accepted", "processing"}:
            return
        raise RuntimeError(message)

    def _to_rfc3339(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
