import { useCallback, useState } from "react";
import { API_BASE_URL, CHANNEL_ID, SESSION_ID } from "../config";
import { useFlowStore } from "../store";
import type { ChatMessage, ChatResponse } from "../types";

function genId(): string {
  return crypto.randomUUID();
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const setCurrentTopicNodeId = useFlowStore((s) => s.setCurrentTopicNodeId);

  const sendMessage = useCallback(
    async (text: string, forceNewTopic: boolean) => {
      const userMsg: ChatMessage = {
        id: genId(),
        role: "user",
        text,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const res = await fetch(`${API_BASE_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            channel_id: CHANNEL_ID,
            session_id: SESSION_ID,
            message: text,
            force_new_topic: forceNewTopic,
          }),
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data: ChatResponse = await res.json();

        setCurrentTopicNodeId(data.topic_node_id);

        const assistantMsg: ChatMessage = {
          id: genId(),
          role: "assistant",
          text: data.assistant_text,
          topicNodeId: data.topic_node_id,
          topicSummary: data.topic_summary,
          contextItemsUsed: data.context_items_used,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMsg: ChatMessage = {
          id: genId(),
          role: "error",
          text: err instanceof Error ? err.message : "Request failed",
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setLoading(false);
      }
    },
    [setCurrentTopicNodeId],
  );

  return { messages, loading, sendMessage };
}
