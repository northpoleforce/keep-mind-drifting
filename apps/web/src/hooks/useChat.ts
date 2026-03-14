import { useCallback, useState } from "react";
import type { ChatMessage, ChatResponse } from "../types";

const sessionId = "demo-session-001";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

let nextId = 0;

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = useCallback(async (text: string, forceNewTopic: boolean) => {
    const userMsg: ChatMessage = {
      id: `msg-${nextId++}`,
      role: "user",
      text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch(`${apiBaseUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_id: "demo-channel",
          session_id: sessionId,
          message: text,
          force_new_topic: forceNewTopic,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data: ChatResponse = await res.json();
      const assistantMsg: ChatMessage = {
        id: `msg-${nextId++}`,
        role: "assistant",
        text: data.assistant_text,
        topicNodeId: data.topic_node_id,
        contextItemsUsed: data.context_items_used,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: `msg-${nextId++}`,
        role: "assistant",
        text: `Error: ${err instanceof Error ? err.message : "Request failed"}`,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { messages, loading, sendMessage };
}
