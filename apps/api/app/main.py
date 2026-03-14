from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .cache import SessionCache, TTLDict
from .config import get_settings
from .evermemos_client import EvermemosClient
from .flow_manager import FlowSocketManager
from .llm_gateway import build_llm_gateway
from .models import ChatRequest, ChatResponse, ContextItem, ContextQuery, FlowEvent, MessageRecord, MockNodeRequest, TopicNodeRecord
from .topic_detector import decide_topic_llm

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await memory.close()


app = FastAPI(title="Evermind Demo API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_frontend_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = EvermemosClient(settings)
llm = build_llm_gateway(settings)
topic_llm_client = llm.client  # reuse the same AsyncOpenAI instance
# NOTE: In-process state — requires single-worker deployment (uvicorn --workers 1).
# For multi-worker / multi-instance, replace with Redis or equivalent shared store.
socket_manager = FlowSocketManager()
session_cache = SessionCache(max_items=30)
last_topic_by_session: TTLDict[str, str] = TTLDict(ttl_seconds=3600)
last_node_by_session: TTLDict[str, str] = TTLDict(ttl_seconds=3600)


def _merge_context(
    cache_items: list[ContextItem],
    memory_items: list[ContextItem],
) -> list[ContextItem]:
    """Weighted merge, dedup, sort — per retrieval-strategy.md."""
    cw = settings.retrieval_cache_weight
    mw = settings.retrieval_memory_weight

    seen: dict[str, ContextItem] = {}
    for item in cache_items:
        key = item.text.strip()
        scored = ContextItem(text=item.text, score=cw * item.score, source=item.source)
        if key not in seen or scored.score > seen[key].score:
            seen[key] = scored
    for item in memory_items:
        key = item.text.strip()
        scored = ContextItem(text=item.text, score=mw * item.score, source=item.source)
        if key not in seen or scored.score > seen[key].score:
            seen[key] = scored

    return sorted(seen.values(), key=lambda c: c.score, reverse=True)


def _fallback_assistant_text(user_message: str) -> str:
    """Return a deterministic local fallback when upstream LLM is unavailable."""
    return (
        "当前 LLM 服务暂不可用，我先给你一个可执行的简版计划：\n"
        "1) 用 15 分钟明确目标与完成标准\n"
        "2) 用 60 分钟完成最重要的一项任务\n"
        "3) 用 20 分钟整理结果并列出下一步\n"
        f"（你的输入：{user_message}）"
    )


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "api", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/health/evermemos")
async def health_evermemos() -> dict:
    try:
        ok = await memory.ping()
        return {"ok": ok}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}


@app.get("/health/llm")
async def health_llm() -> dict:
    try:
        return await llm.healthcheck()
    except Exception as exc:  # pragma: no cover
        return {
            "ok": False,
            "provider": settings.llm_provider,
            "base_url": settings.llm_base_url,
            "model": settings.llm_model,
            "error": str(exc),
        }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    previous_topic = last_topic_by_session.get(req.session_id)
    topic_model = settings.topic_detection_model or settings.llm_model
    decision = await decide_topic_llm(
        topic_llm_client,
        topic_model,
        req.message,
        previous_topic,
        req.force_new_topic,
        max_tokens=settings.topic_detection_max_tokens,
    )
    current_node_id = last_node_by_session.get(req.session_id)

    if decision.is_new_topic:
        topic_node_id = f"tn_{uuid4().hex[:10]}"
        # Only set parent if this is a subtopic of the current topic;
        # otherwise it's a sibling (independent root in the graph).
        graph_parent_id = current_node_id if decision.is_subtopic else None
    else:
        # Same topic continues — reuse existing node, no new graph node
        topic_node_id = current_node_id or f"tn_{uuid4().hex[:10]}"
        graph_parent_id = None

    message_record = MessageRecord(
        channel_id=req.channel_id,
        session_id=req.session_id,
        message_id=f"m_{uuid4().hex[:10]}",
        role="user",
        text=req.message,
        topic_node_id=topic_node_id,
        metadata={"detector": "topic-llm", "is_new_topic": decision.is_new_topic, "is_subtopic": decision.is_subtopic},
    )

    if decision.is_new_topic:
        topic_node_record = TopicNodeRecord(
            channel_id=req.channel_id,
            session_id=req.session_id,
            topic_node_id=topic_node_id,
            parent_topic_node_id=graph_parent_id,
            topic_summary=decision.summary,
            confidence=decision.confidence,
        )
        try:
            await memory.save_message(message_record)
            await memory.save_topic_node(topic_node_record)
        except Exception as exc:
            logger.warning("Evermemos write failed (new topic), continue without memory write: %s", exc)
    else:
        try:
            await memory.save_message(message_record)
        except Exception as exc:
            logger.warning("Evermemos write failed (message), continue without memory write: %s", exc)

    session_cache.add(req.session_id, req.message)
    memory_items = []
    try:
        memory_items = await memory.query_context(
            ContextQuery(channel_id=req.channel_id, session_id=req.session_id, text=req.message, limit=5)
        )
    except Exception:
        memory_items = []

    cache_items = session_cache.query(req.session_id, limit=5)
    merged_items = _merge_context(cache_items, memory_items)
    context_items_used = len(merged_items)

    try:
        llm_result = await llm.generate(
            session_id=req.session_id,
            user_message=req.message,
            context_items=merged_items,
        )
        assistant_text = llm_result.text
    except Exception as exc:
        logger.warning("LLM call failed, fallback to local response: %s", exc)
        assistant_text = _fallback_assistant_text(req.message)

    assistant_record = MessageRecord(
        channel_id=req.channel_id,
        session_id=req.session_id,
        message_id=f"m_{uuid4().hex[:10]}",
        role="assistant",
        text=assistant_text,
        topic_node_id=topic_node_id,
        metadata={"provider": settings.llm_provider, "model": settings.llm_model},
    )

    try:
        await memory.save_message(assistant_record)
    except Exception as exc:
        logger.warning("Evermemos write failed (assistant), continue without memory write: %s", exc)

    # Always update topic summary so drift detection stays accurate.
    last_topic_by_session[req.session_id] = decision.summary

    if decision.is_new_topic:
        last_node_by_session[req.session_id] = topic_node_id

        event = FlowEvent(
            session_id=req.session_id,
            node_id=topic_node_id,
            parent_node_id=graph_parent_id,
            summary=decision.summary,
        )
        await socket_manager.broadcast(req.session_id, {"type": "flow.node.created", "payload": event.model_dump(mode="json")})

    session_cache.add(req.session_id, assistant_text)

    return ChatResponse(
        session_id=req.session_id,
        topic_node_id=topic_node_id,
        topic_summary=decision.summary,
        assistant_text=assistant_text,
        context_items_used=context_items_used,
    )


@app.websocket("/ws/flow/{session_id}")
async def ws_flow(websocket: WebSocket, session_id: str) -> None:
    await socket_manager.connect(session_id, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
    except WebSocketDisconnect:
        socket_manager.disconnect(session_id, websocket)


@app.post("/demo/mock-node")
async def mock_node(req: MockNodeRequest) -> dict:
    node_id = f"mock_{uuid4().hex[:10]}"
    event = FlowEvent(
        session_id=req.session_id,
        node_id=node_id,
        parent_node_id=req.parent_node_id,
        summary=req.summary,
    )
    await socket_manager.broadcast(req.session_id, {"type": "flow.node.created", "payload": event.model_dump(mode="json")})
    return {"ok": True, "node_id": node_id}
