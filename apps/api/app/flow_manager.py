from collections import defaultdict

from fastapi import WebSocket


class FlowSocketManager:
    def __init__(self) -> None:
        self._sessions: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._sessions[session_id].add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].discard(websocket)

    async def broadcast(self, session_id: str, payload: dict) -> None:
        sockets = list(self._sessions.get(session_id, set()))
        for socket in sockets:
            await socket.send_json(payload)
