import { create } from "zustand";
import type { Node, Edge } from "@xyflow/react";

export type WsStatus = "connecting" | "connected" | "disconnected";

interface FlowStore {
  // --- flow graph state ---
  nodes: Node[];
  edges: Edge[];
  wsStatus: WsStatus;
  currentTopicNodeId: string | null;

  addFlowNode: (
    nodeId: string,
    parentNodeId: string | null,
    summary: string,
  ) => void;
  setWsStatus: (status: WsStatus) => void;
  setCurrentTopicNodeId: (id: string | null) => void;
  resetFlow: () => void;
}

/**
 * Compute tree-based positions from adjacency.
 *
 * Strategy: BFS layer-by-layer.  Each layer is a row (increasing y).
 * Within each row, children are centered under their parent.
 */
const NODE_W = 200;
const NODE_GAP_X = 40;
const NODE_GAP_Y = 100;

function layoutTree(nodes: Node[], edges: Edge[]): Node[] {
  if (nodes.length === 0) return [];

  // Build child map
  const children: Record<string, string[]> = {};
  const hasParent = new Set<string>();
  for (const e of edges) {
    if (!children[e.source]) children[e.source] = [];
    children[e.source].push(e.target);
    hasParent.add(e.target);
  }

  // Find roots (nodes with no incoming edge)
  const roots = nodes.filter((n) => !hasParent.has(n.id)).map((n) => n.id);
  if (roots.length === 0) {
    // fallback: treat first node as root
    roots.push(nodes[0].id);
  }

  // BFS to assign layers
  const layer: Record<string, number> = {};
  const queue = [...roots];
  roots.forEach((r) => (layer[r] = 0));

  while (queue.length > 0) {
    const id = queue.shift()!;
    for (const child of children[id] || []) {
      if (layer[child] === undefined) {
        layer[child] = layer[id] + 1;
        queue.push(child);
      }
    }
  }

  // Assign layers to orphans (disconnected nodes)
  let maxLayer = 0;
  for (const v of Object.values(layer)) {
    if (v > maxLayer) maxLayer = v;
  }
  // All orphans share the same extra layer so they sit side-by-side,
  // not stacked one-per-row (which ++maxLayer would cause).
  const orphanLayer = maxLayer + 1;
  for (const n of nodes) {
    if (layer[n.id] === undefined) {
      layer[n.id] = orphanLayer;
    }
  }

  // Group by layer
  const layers: Record<number, string[]> = {};
  for (const [id, l] of Object.entries(layer)) {
    if (!layers[l]) layers[l] = [];
    layers[l].push(id);
  }

  // Assign positions
  const posMap: Record<string, { x: number; y: number }> = {};
  const totalLayers = Math.max(...Object.keys(layers).map(Number)) + 1;

  for (let l = 0; l < totalLayers; l++) {
    const ids = layers[l] || [];
    const rowWidth = ids.length * NODE_W + (ids.length - 1) * NODE_GAP_X;
    const startX = -rowWidth / 2;
    ids.forEach((id, i) => {
      posMap[id] = {
        x: startX + i * (NODE_W + NODE_GAP_X),
        y: l * (60 + NODE_GAP_Y),
      };
    });
  }

  return nodes.map((n) => ({
    ...n,
    position: posMap[n.id] || n.position,
  }));
}

export const useFlowStore = create<FlowStore>((set) => ({
  nodes: [],
  edges: [],
  wsStatus: "connecting",
  currentTopicNodeId: null,

  addFlowNode: (nodeId, parentNodeId, summary) =>
    set((state) => {
      // Dedup: skip if node already exists
      if (state.nodes.some((n) => n.id === nodeId)) return state;

      const newNode: Node = {
        id: nodeId,
        position: { x: 0, y: 0 }, // will be overwritten by layout
        data: { label: summary },
      };

      const newEdges = [...state.edges];
      if (parentNodeId && state.nodes.some((n) => n.id === parentNodeId)) {
        newEdges.push({
          id: `${parentNodeId}-${nodeId}`,
          source: parentNodeId,
          target: nodeId,
        });
      }

      const rawNodes = [...state.nodes, newNode];
      return {
        nodes: layoutTree(rawNodes, newEdges),
        edges: newEdges,
      };
    }),

  setWsStatus: (status) => set({ wsStatus: status }),
  setCurrentTopicNodeId: (id) => set({ currentTopicNodeId: id }),
  resetFlow: () => set({ nodes: [], edges: [], currentTopicNodeId: null }),
}));
