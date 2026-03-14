import type { ChatMessage } from "../types";

type Props = {
  message: ChatMessage;
};

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`bubble-row ${isUser ? "bubble-row--user" : "bubble-row--assistant"}`}>
      <div className={`bubble ${isUser ? "bubble--user" : "bubble--assistant"}`}>
        <p className="bubble__text">{message.text}</p>
        {!isUser && message.contextItemsUsed !== undefined && message.contextItemsUsed > 0 && (
          <span className="bubble__context">
            Cited {message.contextItemsUsed} context item{message.contextItemsUsed > 1 ? "s" : ""}
          </span>
        )}
      </div>
    </div>
  );
}
