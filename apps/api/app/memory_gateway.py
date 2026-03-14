from abc import ABC, abstractmethod

from .models import ContextItem, ContextQuery, MessageRecord, TopicNodeRecord


class MemoryGateway(ABC):
    @abstractmethod
    async def ping(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def save_message(self, record: MessageRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_topic_node(self, record: TopicNodeRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    async def query_context(self, query: ContextQuery) -> list[ContextItem]:
        raise NotImplementedError

    @abstractmethod
    async def rebuild_flow(self, channel_id: str, session_id: str) -> list[dict]:
        raise NotImplementedError
