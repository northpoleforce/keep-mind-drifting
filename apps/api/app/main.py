from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .cache import SessionCache
from .config import get_settings
from .evermemos_client import EvermemosClient
from .flow_manager import FlowSocketManager
from .llm_gateway import build_llm_gateway
from .models import ChatRequest, ChatResponse, ContextQuery, FlowEvent, MessageRecord, MockNodeRequest, TopicNodeRecord
from .topic_detector import decide_topic

settings = get_settings()
app = FastAPI(title="Evermind Demo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = EvermemosClient(settings)
llm = build_llm_gateway(settings)
socket_manager = FlowSocketManager()
session_cache = SessionCache(max_items=30)
last_topic_by_session: dict[str, str] = {}
last_node_by_session: dict[str, str] = {}


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "api", "time": datetime.utcnow().isoformat()}


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
    decision = decide_topic(req.message, previous_topic, req.force_new_topic)
    parent_node_id = last_node_by_session.get(req.session_id)
    topic_node_id = f"tn_{uuid4().hex[:10]}"

    message_record = MessageRecord(
        channel_id=req.channel_id,
        session_id=req.session_id,
        message_id=f"m_{uuid4().hex[:10]}",
        role="user",
        text=req.message,
        topic_node_id=topic_node_id,
        metadata={"detector": "high-sensitivity-heuristic"},
    )
    topic_node_record = TopicNodeRecord(
        channel_id=req.channel_id,
        session_id=req.session_id,
        topic_node_id=topic_node_id,
        parent_topic_node_id=parent_node_id,
        topic_summary=decision.summary,
        confidence=decision.confidence,
    )

    try:
        await memory.save_message(message_record)
        await memory.save_topic_node(topic_node_record)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Evermemos write failed: {exc}") from exc

    session_cache.add(req.session_id, req.message)
    memory_items = []
    try:
        memory_items = await memory.query_context(
            ContextQuery(channel_id=req.channel_id, session_id=req.session_id, text=req.message, limit=5)
        )
    except Exception:
        memory_items = []

    cache_items = session_cache.query(req.session_id, limit=5)
    merged_items = cache_items + memory_items
    context_items_used = len(merged_items)

    try:
        llm_result = await llm.generate(
            session_id=req.session_id,
            user_message=req.message,
            context_items=merged_items,
        )
        assistant_text = llm_result.text
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

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
        raise HTTPException(status_code=502, detail=f"Evermemos write failed (assistant): {exc}") from exc

    last_topic_by_session[req.session_id] = decision.summary
    last_node_by_session[req.session_id] = topic_node_id

    event = FlowEvent(
        session_id=req.session_id,
        node_id=topic_node_id,
        parent_node_id=parent_node_id,
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


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await memory.close()
