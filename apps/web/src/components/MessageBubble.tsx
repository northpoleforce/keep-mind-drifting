import type { ChatMessage } from "../types";

type Props = {
  message: ChatMessage;
};

export function MessageBubble({ message }: Props) {
  if (message.role === "error") {
    return (
      <div className="bubble-row bubble-row--assistant">
        <div className="bubble bubble--error">
          <p className="bubble__text">{message.text}</p>
        </div>
      </div>
    );
  }

  const isUser = message.role === "user";

  return (
    <div
      className={`bubble-row ${isUser ? "bubble-row--user" : "bubble-row--assistant"}`}
    >
      <div className={`bubble ${isUser ? "bubble--user" : "bubble--assistant"}`}>
        <p className="bubble__text">{message.text}</p>
        {!isUser && message.topicSummary && (
          <span className="bubble__topic">{message.topicSummary}</span>
        )}
        {!isUser &&
          message.contextItemsUsed !== undefined &&
          message.contextItemsUsed > 0 && (
            <span className="bubble__context">
              Cited {message.contextItemsUsed} context item
              {message.contextItemsUsed > 1 ? "s" : ""}
            </span>
          )}
      </div>
    </div>
  );
}
