import { ReactFlow, Background, Controls } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useFlowSocket } from "../hooks/useFlowSocket";
import "./FlowPanel.css";

export function FlowPanel() {
  const { nodes, edges } = useFlowSocket();

  return (
    <main className="flow-panel">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </main>
  );
}
