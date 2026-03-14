import { useEffect, useRef } from "react";
import { SESSION_ID, WS_BASE_URL } from "../config";
import { useFlowStore } from "../store";
import type { FlowMessage } from "../types";

const MAX_RECONNECT_DELAY = 30_000;

export function useFlowSocket() {
  const { addFlowNode, setWsStatus } = useFlowStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const bootstrapTimer = useRef<ReturnType<typeof setTimeout>>();
  const attempt = useRef(0);
  const shouldReconnectRef = useRef(true);

  useEffect(() => {
    shouldReconnectRef.current = true;

    function connect() {
      if (!shouldReconnectRef.current) return;

      // If a socket is already live/connecting, don't create a duplicate.
      const prev = wsRef.current;
      if (prev && (prev.readyState === WebSocket.OPEN || prev.readyState === WebSocket.CONNECTING)) {
        return;
      }

      setWsStatus("connecting");
      const ws = new WebSocket(`${WS_BASE_URL}/ws/flow/${SESSION_ID}`);
      wsRef.current = ws;

      ws.onopen = () => {
        attempt.current = 0;
        setWsStatus("connected");
      };

      ws.onmessage = (event) => {
        let data: FlowMessage;
        try {
          data = JSON.parse(event.data);
        } catch {
          return; // e.g. pong or malformed
        }
        if (data.type !== "flow.node.created") return;
        const p = data.payload;
        addFlowNode(p.node_id, p.parent_node_id, p.summary);
      };

      ws.onclose = () => {
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
        setWsStatus("disconnected");
        if (shouldReconnectRef.current) {
          scheduleReconnect();
        }
      };

      ws.onerror = () => {
        // onclose will fire after onerror; reconnect handled there
      };
    }

    function scheduleReconnect() {
      if (!shouldReconnectRef.current) return;
      const delay = Math.min(1000 * 2 ** attempt.current, MAX_RECONNECT_DELAY);
      attempt.current += 1;
      reconnectTimer.current = setTimeout(connect, delay);
    }

    // Defer initial connect so StrictMode's throwaway mount can cleanly cancel.
    bootstrapTimer.current = setTimeout(connect, 0);

    return () => {
      shouldReconnectRef.current = false;
      clearTimeout(bootstrapTimer.current);
      clearTimeout(reconnectTimer.current);
      const ws = wsRef.current;
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null; // prevent reconnect on intentional close
        try {
          ws.close(1000, "component unmount");
        } catch {
          // noop
        }
        wsRef.current = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}
