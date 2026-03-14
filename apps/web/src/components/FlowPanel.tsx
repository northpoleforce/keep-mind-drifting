import { useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useFlowSocket } from "../hooks/useFlowSocket";
import { useFlowStore } from "../store";
import type { WsStatus } from "../store";
import "./FlowPanel.css";

function statusLabel(s: WsStatus) {
  if (s === "connected") return "Connected";
  if (s === "connecting") return "Connecting...";
  return "Disconnected";
}

function FlowInner() {
  useFlowSocket();

  const nodes = useFlowStore((s) => s.nodes);
  const edges = useFlowStore((s) => s.edges);
  const wsStatus = useFlowStore((s) => s.wsStatus);
  const currentTopicNodeId = useFlowStore((s) => s.currentTopicNodeId);
  const { fitView } = useReactFlow();

  // Highlight current topic node
  const styledNodes = useMemo(
    () =>
      nodes.map((n) => ({
        ...n,
        style:
          n.id === currentTopicNodeId
            ? {
                border: "2px solid #3b82f6",
                borderRadius: 8,
                background: "#eff6ff",
              }
            : undefined,
      })),
    [nodes, currentTopicNodeId],
  );

  // Auto fitView when nodes change
  useEffect(() => {
    if (nodes.length === 0) return;
    // Small delay to let ReactFlow render the new nodes
    const id = setTimeout(() => fitView({ padding: 0.3, duration: 300 }), 50);
    return () => clearTimeout(id);
  }, [nodes.length, fitView]);

  return (
    <main className="flow-panel">
      <div className={`flow-panel__status flow-panel__status--${wsStatus}`}>
        {statusLabel(wsStatus)}
      </div>
      <ReactFlow nodes={styledNodes} edges={edges}>
        <Background />
        <Controls />
      </ReactFlow>
    </main>
  );
}

export function FlowPanel() {
  return (
    <ReactFlowProvider>
      <FlowInner />
    </ReactFlowProvider>
  );
}
