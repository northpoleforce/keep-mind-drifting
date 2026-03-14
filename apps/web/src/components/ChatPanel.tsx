import { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import "./ChatPanel.css";

export function ChatPanel() {
  const { messages, loading, sendMessage } = useChat();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const canSend = input.trim().length > 0 && !loading;

  function handleSubmit(forceNewTopic: boolean) {
    if (!canSend) return;
    const text = input.trim();
    setInput("");
    sendMessage(text, forceNewTopic);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(false);
    }
  }

  return (
    <aside className="chat-panel">
      <header className="chat-panel__header">
        <h2>Evermind</h2>
      </header>

      <div className="chat-panel__messages">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {loading && (
          <div className="bubble-row bubble-row--assistant">
            <div className="bubble bubble--assistant typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-panel__input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          placeholder="Type a message..."
        />
        <div className="chat-panel__actions">
          <button className="btn btn--primary" onClick={() => handleSubmit(false)} disabled={!canSend}>
            Send
          </button>
          <button className="btn btn--secondary" onClick={() => handleSubmit(true)} disabled={!canSend}>
            New Topic
          </button>
        </div>
      </div>
    </aside>
  );
}
