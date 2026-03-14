# Architecture (Draft)

## Flow

1. User sends message from web app.
2. API decides topic (high-sensitivity mode).
3. API writes message + topic node to Evermemos.
4. API queries mixed context (cache + Evermemos).
5. API emits flow event through WebSocket.
