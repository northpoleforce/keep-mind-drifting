export type FlowNodeCreatedEvent = {
  type: "flow.node.created";
  payload: {
    session_id: string;
    node_id: string;
    parent_node_id: string | null;
    summary: string;
    timestamp: string;
  };
};
