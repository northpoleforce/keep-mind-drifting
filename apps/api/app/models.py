from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    channel_id: str
    session_id: str
    message: str
    force_new_topic: bool = False


class ChatResponse(BaseModel):
    session_id: str
    topic_node_id: str
    topic_summary: str
    assistant_text: str
    context_items_used: int


class MessageRecord(BaseModel):
    channel_id: str
    session_id: str
    message_id: str
    role: str
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    topic_node_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicNodeRecord(BaseModel):
    channel_id: str
    session_id: str
    topic_node_id: str
    parent_topic_node_id: Optional[str] = None
    topic_summary: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextQuery(BaseModel):
    channel_id: str
    session_id: str
    text: str
    limit: int = 8


class ContextItem(BaseModel):
    text: str
    score: float
    source: str


class FlowEvent(BaseModel):
    session_id: str
    node_id: str
    parent_node_id: Optional[str]
    summary: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MockNodeRequest(BaseModel):
    session_id: str
    summary: str
    parent_node_id: Optional[str] = None
