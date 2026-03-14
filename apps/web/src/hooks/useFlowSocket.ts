import { useEffect, useState } from "react";
import type { FlowMessage } from "../types";

const sessionId = "demo-session-001";
const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || "ws://127.0.0.1:8000";

export function useFlowSocket() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);

  useEffect(() => {
    const ws = new WebSocket(`${wsBaseUrl}/ws/flow/${sessionId}`);
    ws.onmessage = (event) => {
      const data: FlowMessage = JSON.parse(event.data);
      if (data.type !== "flow.node.created") return;
      const p = data.payload;
      setNodes((prev) => {
        const index = prev.length;
        return [
          ...prev,
          {
            id: p.node_id,
            position: { x: 220 * (index % 3), y: 140 * Math.floor(index / 3) },
            data: { label: p.summary },
          },
        ];
      });
      if (p.parent_node_id) {
        setEdges((prev) => [
          ...prev,
          {
            id: `${p.parent_node_id}-${p.node_id}`,
            source: p.parent_node_id,
            target: p.node_id,
          },
        ]);
      }
    };
    return () => ws.close();
  }, []);

  return { nodes, edges };
}
