// components/MessageBubble.jsx
// Renders a single chat message with rich code formatting, copy buttons,
// timestamps, and optional text-to-speech.

import { useState } from "react";

/**
 * Format markdown text: handles code blocks, inline code, bold text, and bullet points.
 */
function MarkdownRenderer({ content }) {
  // Regex to split on code blocks: ```lang\ncode\n```
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: "text",
        value: content.substring(lastIndex, match.index),
      });
    }
    parts.push({
      type: "code",
      language: match[1] || "code",
      code: match[2].trim(),
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({
      type: "text",
      value: content.substring(lastIndex),
    });
  }

  return (
    <div className="markdown-body">
      {parts.map((part, idx) => {
        if (part.type === "code") {
          return <CodeBlock key={idx} language={part.language} code={part.code} />;
        }
        return <TextBlock key={idx} text={part.value} />;
      })}
    </div>
  );
}

/**
 * Code block with language tag and a Copy Code button.
 */
function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="code-block-container">
      <div className="code-block-header">
        <span className="code-language">{language.toUpperCase()}</span>
        <button className="code-copy-btn" onClick={handleCopy}>
          {copied ? "✓ Copied!" : "📋 Copy Code"}
        </button>
      </div>
      <pre className="code-block-content">
        <code>{code}</code>
      </pre>
    </div>
  );
}

/**
 * Render paragraphs, bold text, inline code, and bullet lists.
 */
function TextBlock({ text }) {
  const lines = text.split("\n");

  return (
    <>
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={idx} style={{ height: "6px" }} />;

        // Bullet point
        if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
          return (
            <div key={idx} className="bullet-point">
              <span className="bullet-dot">•</span>
              <span>{formatInline(trimmed.substring(2))}</span>
            </div>
          );
        }

        return (
          <p key={idx} className="message-paragraph">
            {formatInline(line)}
          </p>
        );
      })}
    </>
  );
}

/**
 * Parses **bold** and `inline code`
 */
function formatInline(str) {
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  const tokens = str.split(regex);

  return tokens.map((token, i) => {
    if (token.startsWith("**") && token.endsWith("**")) {
      return <strong key={i}>{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith("`") && token.endsWith("`")) {
      return <code key={i} className="inline-code">{token.slice(1, -1)}</code>;
    }
    return token;
  });
}

export default function MessageBubble({ role, text, timestamp, isNew }) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  // Copy full message
  function handleCopyMessage() {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // Text-To-Speech (Native Web Speech API - free & offline)
  function handleToggleSpeech() {
    if (!("speechSynthesis" in window)) return;

    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
    } else {
      window.speechSynthesis.cancel(); // stop any current speech
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      window.speechSynthesis.speak(utterance);
      setSpeaking(true);
    }
  }

  return (
    <div
      className={`message-row ${isUser ? "message-row--user" : "message-row--ai"} ${
        isNew ? "message-row--new" : ""
      }`}
    >
      {/* Avatar */}
      <div className={`avatar ${isUser ? "avatar--user" : "avatar--ai"}`}>
        {isUser ? "🧑" : "🤖"}
      </div>

      {/* Bubble */}
      <div className={`bubble ${isUser ? "bubble--user" : "bubble--ai"}`}>
        <MarkdownRenderer content={text} />

        {/* Message Footer: Timestamp & Action Buttons */}
        <div className="message-footer">
          {timestamp && <span className="message-time">{timestamp}</span>}

          {!isUser && (
            <div className="message-actions">
              <button
                className="action-icon-btn"
                onClick={handleCopyMessage}
                title="Copy response"
              >
                {copied ? "✓" : "📋"}
              </button>
              {"speechSynthesis" in window && (
                <button
                  className={`action-icon-btn ${speaking ? "action-icon-btn--active" : ""}`}
                  onClick={handleToggleSpeech}
                  title={speaking ? "Stop speaking" : "Read aloud"}
                >
                  {speaking ? "⏹️" : "🔊"}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
