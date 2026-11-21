// components/ChatWindow.jsx
// Displays the scrollable list of messages with auto-scroll and
// interactive starter prompt cards for quick learning topics.

import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

const QUICK_PROMPTS = [
  { icon: "💡", label: "Recursion Analogy", prompt: "Explain Python recursion using a simple real-world analogy." },
  { icon: "⚡", label: "REST APIs", prompt: "What is an API and how does REST work? Give a beginner example." },
  { icon: "🚀", label: "SQL vs NoSQL", prompt: "What is the difference between SQL and NoSQL databases?" },
  { icon: "🐛", label: "Debug Python Loop", prompt: "Why do I get an IndexError in Python and how do I fix it?" },
];

/**
 * Loading indicator shown while waiting for the AI to respond.
 */
function TypingIndicator() {
  return (
    <div className="message-row message-row--ai">
      <div className="avatar avatar--ai">🤖</div>
      <div className="bubble bubble--ai bubble--typing">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}

/**
 * Quick prompt suggestions shown when the conversation is fresh.
 */
function QuickSuggestions({ onSelectPrompt }) {
  return (
    <div className="quick-suggestions-container">
      <p className="suggestions-header">✨ Try asking one of these:</p>
      <div className="suggestions-grid">
        {QUICK_PROMPTS.map((item, idx) => (
          <button
            key={idx}
            className="suggestion-card"
            onClick={() => onSelectPrompt(item.prompt)}
          >
            <span className="suggestion-icon">{item.icon}</span>
            <span className="suggestion-label">{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatWindow({ messages, isLoading, onSelectPrompt }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const showSuggestions = messages.length <= 1 && !isLoading;

  return (
    <div className="chat-window">
      {messages.map((msg, idx) => (
        <MessageBubble
          key={idx}
          role={msg.role}
          text={msg.text}
          timestamp={msg.timestamp}
          isNew={idx === messages.length - 1}
        />
      ))}

      {/* Quick starter prompts */}
      {showSuggestions && <QuickSuggestions onSelectPrompt={onSelectPrompt} />}

      {/* Show animated typing dots while waiting for AI */}
      {isLoading && <TypingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
}
