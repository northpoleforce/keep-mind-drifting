import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactFlow, Background, Controls } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useState } from "react";

type FlowPayload = {
  node_id: string;
  parent_node_id: string | null;
  summary: string;
  session_id: string;
  timestamp: string;
};

type FlowMessage = {
  type: string;
  payload: FlowPayload;
};

const queryClient = new QueryClient();
const sessionId = "demo-session-001";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || "ws://127.0.0.1:8000";

function App() {
  const [input, setInput] = useState("");
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
        setEdges((prev) => [...prev, { id: `${p.parent_node_id}-${p.node_id}`, source: p.parent_node_id, target: p.node_id }]);
      }
    };
    return () => ws.close();
  }, []);

  const canSend = useMemo(() => input.trim().length > 0, [input]);

  async function submitMessage(forceNewTopic: boolean) {
    if (!canSend) return;
    await fetch(`${apiBaseUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel_id: "demo-channel",
        session_id: sessionId,
        message: input,
        force_new_topic: forceNewTopic,
      }),
    });
    setInput("");
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", height: "100vh" }}>
      <aside style={{ borderRight: "1px solid #d6d6d6", padding: "16px" }}>
        <h2 style={{ marginTop: 0 }}>Evermind Demo</h2>
        <p style={{ fontSize: 14, lineHeight: 1.4 }}>
          Real-time thought-flow demo with Evermemos as the core memory store.
        </p>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={8}
          style={{ width: "100%", marginBottom: 8 }}
          placeholder="Type a user message..."
        />
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => submitMessage(false)} disabled={!canSend}>
            Send
          </button>
          <button onClick={() => submitMessage(true)} disabled={!canSend}>
            Force New Topic
          </button>
        </div>
      </aside>
      <main>
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background />
          <Controls />
        </ReactFlow>
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
