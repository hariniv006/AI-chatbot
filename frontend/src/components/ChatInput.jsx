// components/ChatInput.jsx
// Input textarea with real-time character count and clear button.

import { useState } from "react";

const MAX_CHAR_LIMIT = 2000;

export default function ChatInput({ onSendMessage, isLoading, isDisabled }) {
  const [inputValue, setInputValue] = useState("");

  function handleSubmit(e) {
    if (e) e.preventDefault();

    const trimmed = inputValue.trim();
    if (!trimmed || isLoading || isDisabled) return;

    onSendMessage(trimmed);
    setInputValue("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleClear() {
    setInputValue("");
  }

  const charCount = inputValue.length;
  const isOverLimit = charCount > MAX_CHAR_LIMIT;

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <div className="chat-input-wrapper">
        <textarea
          className="chat-input-textarea"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isDisabled
              ? "Click 'New Chat' to start a conversation…"
              : "Ask Lexi anything… (Enter to send, Shift+Enter for new line)"
          }
          disabled={isLoading || isDisabled}
          rows={2}
          maxLength={MAX_CHAR_LIMIT + 50}
        />

        {inputValue.trim() && !isLoading && (
          <button
            type="button"
            className="input-clear-btn"
            onClick={handleClear}
            title="Clear text"
          >
            ✕
          </button>
        )}

        <div className={`char-counter ${isOverLimit ? "char-counter--danger" : ""}`}>
          {charCount} / {MAX_CHAR_LIMIT}
        </div>
      </div>

      <button
        type="submit"
        className="chat-input-btn"
        disabled={isLoading || isDisabled || !inputValue.trim() || isOverLimit}
        title="Send message"
      >
        {isLoading ? (
          <span className="btn-spinner" />
        ) : (
          <span>Send ➤</span>
        )}
      </button>
    </form>
  );
}
