export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  topicNodeId?: string;
  contextItemsUsed?: number;
  timestamp: number;
};

export type FlowPayload = {
  node_id: string;
  parent_node_id: string | null;
  summary: string;
  session_id: string;
  timestamp: string;
};

export type FlowMessage = {
  type: string;
  payload: FlowPayload;
};

export type ChatResponse = {
  session_id: string;
  topic_node_id: string;
  topic_summary: string;
  assistant_text: string;
  context_items_used: number;
};
