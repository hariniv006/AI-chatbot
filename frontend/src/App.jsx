// App.jsx
// Root component – manages authentication, sidebar conversation history,
// chat messages, health checks, quick starters, and audio TTS.

import { useState, useEffect, useCallback } from "react";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import LoginPage from "./components/LoginPage";
import Sidebar from "./components/Sidebar";
import {
  checkHealth,
  createNewChat,
  sendMessage,
  clearConversation,
  getConversations,
  getChatDetail,
  deleteConversation,
} from "./services/api";
import "./App.css";

function formatCurrentTime() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const WELCOME_MESSAGE = {
  role: "assistant",
  text: "👋 Hi! I'm Lexi, your AI learning assistant. What technical topic would you like to explore today?",
  timestamp: formatCurrentTime(),
};

export default function App() {
  // ── Authentication state ──
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem("lexi_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // ── Chat state ──
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [turnCount, setTurnCount] = useState(0);
  const [serverOnline, setServerOnline] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // ─────────────────────────────────────────
  // Fetch user conversations list for sidebar
  // ─────────────────────────────────────────
  const loadConversations = useCallback(async (username) => {
    if (!username) return;
    try {
      const list = await getConversations(username);
      setConversations(list);
    } catch (err) {
      console.warn("Failed to load conversation history:", err);
    }
  }, []);

  // ─────────────────────────────────────────
  // Initial startup: check health & init chat
  // ─────────────────────────────────────────
  useEffect(() => {
    async function init() {
      try {
        await checkHealth();
        setServerOnline(true);
      } catch {
        setServerOnline(false);
        setError("Cannot reach the backend server. Make sure FastAPI is running on port 8000.");
        return;
      }

      if (currentUser?.username) {
        try {
          const list = await getConversations(currentUser.username);
          setConversations(list);

          if (list && list.length > 0) {
            // Load the most recent conversation automatically
            const latest = list[0];
            const detail = await getChatDetail(latest.conversation_id);
            setConversationId(detail.conversation_id);
            if (detail.messages && detail.messages.length > 0) {
              setMessages(detail.messages);
              setTurnCount(detail.messages.length);
            } else {
              setMessages([WELCOME_MESSAGE]);
              setTurnCount(0);
            }
          } else {
            // Start fresh session if no history
            const data = await createNewChat(currentUser.username);
            setConversationId(data.conversation_id);
            setMessages([WELCOME_MESSAGE]);
            setTurnCount(0);
            await loadConversations(currentUser.username);
          }
        } catch (err) {
          console.warn("Init conversation failed:", err);
          const data = await createNewChat(currentUser.username);
          setConversationId(data.conversation_id);
          setMessages([WELCOME_MESSAGE]);
        }
      }
    }

    init();
  }, [currentUser?.username, loadConversations]);

  // ─────────────────────────────────────────
  // Login handler
  // ─────────────────────────────────────────
  async function handleLoginSuccess(userData) {
    try {
      localStorage.setItem("lexi_user", JSON.stringify(userData));
    } catch (e) {
      console.error(e);
    }
    setCurrentUser(userData);
    setError(null);
  }

  // ─────────────────────────────────────────
  // Logout handler
  // ─────────────────────────────────────────
  function handleLogout() {
    try {
      localStorage.removeItem("lexi_user");
    } catch (e) {
      console.error(e);
    }
    setCurrentUser(null);
    setConversationId(null);
    setMessages([]);
    setConversations([]);
    setTurnCount(0);
  }

  // ─────────────────────────────────────────
  // Select a conversation from the sidebar
  // ─────────────────────────────────────────
  async function handleSelectConversation(selectedId) {
    if (selectedId === conversationId) return;

    setError(null);
    setIsLoading(true);

    try {
      const detail = await getChatDetail(selectedId);
      setConversationId(detail.conversation_id);
      if (detail.messages && detail.messages.length > 0) {
        setMessages(detail.messages);
        setTurnCount(detail.messages.length);
      } else {
        setMessages([WELCOME_MESSAGE]);
        setTurnCount(0);
      }
    } catch (err) {
      setError(`Failed to load conversation: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }

  // ─────────────────────────────────────────
  // Start a brand-new chat session
  // ─────────────────────────────────────────
  async function handleNewChat() {
    setError(null);
    setIsLoading(true);

    try {
      const username = currentUser?.username || "guest";
      const data = await createNewChat(username);
      setConversationId(data.conversation_id);
      setMessages([WELCOME_MESSAGE]);
      setTurnCount(0);
      await loadConversations(username);
    } catch (err) {
      setError(`Failed to start new chat: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }

  // ─────────────────────────────────────────
  // Delete a conversation from the sidebar
  // ─────────────────────────────────────────
  async function handleDeleteConversation(deletedId) {
    try {
      await deleteConversation(deletedId);
      const updated = conversations.filter((c) => c.conversation_id !== deletedId);
      setConversations(updated);

      // If we deleted the active conversation, switch or create new
      if (conversationId === deletedId) {
        if (updated.length > 0) {
          handleSelectConversation(updated[0].conversation_id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      setError(`Failed to delete conversation: ${err.message}`);
    }
  }

  // ─────────────────────────────────────────
  // Clear messages in current session
  // ─────────────────────────────────────────
  async function handleClearChat() {
    if (!conversationId) return;
    setError(null);

    try {
      await clearConversation(conversationId);
      setTurnCount(0);
      setMessages([
        {
          role: "assistant",
          text: "🧹 Conversation history cleared. What would you like to learn next?",
          timestamp: formatCurrentTime(),
        },
      ]);
    } catch (err) {
      setError(`Failed to clear conversation: ${err.message}`);
    }
  }

  // ─────────────────────────────────────────
  // Export chat conversation as a text file
  // ─────────────────────────────────────────
  function handleExportChat() {
    if (messages.length === 0) return;

    let transcript = `=== Lexi AI Chat Export ===\n`;
    transcript += `User: ${currentUser?.username || "Guest"}\n`;
    transcript += `Conversation ID: ${conversationId || "N/A"}\n`;
    transcript += `Date: ${new Date().toLocaleString()}\n`;
    transcript += `============================\n\n`;

    messages.forEach((msg) => {
      const speaker = msg.role === "user" ? "USER" : "LEXI (AI)";
      transcript += `[${msg.timestamp || "Time"}] ${speaker}:\n${msg.text}\n\n`;
    });

    const blob = new Blob([transcript], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `chat-export-${(conversationId || "session").slice(0, 8)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  // ─────────────────────────────────────────
  // Send a user message (with 404 auto-recovery & sidebar refresh)
  // ─────────────────────────────────────────
  async function handleSendMessage(text) {
    if (!conversationId) {
      setError("Please click 'New Chat' first to start a conversation.");
      return;
    }

    setError(null);
    const userTimestamp = formatCurrentTime();

    // Optimistically add user bubble to UI
    setMessages((prev) => [
      ...prev,
      { role: "user", text, timestamp: userTimestamp },
    ]);
    setIsLoading(true);

    try {
      let data;
      try {
        data = await sendMessage(conversationId, text);
      } catch (err) {
        // Auto-recover if backend server was restarted
        if (err.message.includes("not found") || err.message.includes("404")) {
          const username = currentUser?.username || "guest";
          const newChat = await createNewChat(username);
          setConversationId(newChat.conversation_id);
          data = await sendMessage(newChat.conversation_id, text);
        } else {
          throw err;
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.response,
          timestamp: formatCurrentTime(),
        },
      ]);
      setTurnCount(data.turn_count);

      // Refresh sidebar conversation list so title updates
      if (currentUser?.username) {
        loadConversations(currentUser.username);
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }

  // ─────────────────────────────────────────
  // If not logged in, render Login Page
  // ─────────────────────────────────────────
  if (!currentUser) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  // ─────────────────────────────────────────
  // Main Chat Layout with Sidebar
  // ─────────────────────────────────────────
  return (
    <div className="app-layout">
      {/* ── Left Sidebar (Past Chat History) ── */}
      <Sidebar
        conversations={conversations}
        activeId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        currentUser={currentUser}
        onLogout={handleLogout}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* ── Main Chat Container ── */}
      <div className="app-container">
        {/* ── Header ── */}
        <header className="app-header">
          <div className="header-left">
            <button
              className="sidebar-toggle-btn"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              title="Toggle chat history sidebar"
            >
              ☰
            </button>
            <span className="header-logo">🤖</span>
            <div>
              <div className="header-title-row">
                <h1 className="header-title">Lexi AI</h1>
                <span className="model-badge">gemini-3.5-flash-lite</span>
              </div>
              <p className="header-subtitle">
                Context-Aware AI Learning Assistant • Logged in as <strong>{currentUser.username}</strong>
              </p>
            </div>
          </div>

          <div className="header-right">
            {/* Server status dot */}
            <span
              className={`status-dot ${
                serverOnline === null
                  ? "status-dot--checking"
                  : serverOnline
                  ? "status-dot--online"
                  : "status-dot--offline"
              }`}
              title={
                serverOnline === null
                  ? "Checking server…"
                  : serverOnline
                  ? "Server online"
                  : "Server offline"
              }
            />

            {/* Turn counter */}
            {turnCount > 0 && (
              <span className="turn-counter">
                {Math.floor(turnCount / 2)} {Math.floor(turnCount / 2) === 1 ? "turn" : "turns"}
              </span>
            )}

            {/* Action buttons */}
            <button
              className="header-icon-btn"
              onClick={handleExportChat}
              title="Export chat as text file"
              disabled={messages.length <= 1}
            >
              📥 Export
            </button>

            <button
              className="header-icon-btn"
              onClick={handleClearChat}
              title="Clear current messages"
              disabled={messages.length <= 1 || isLoading}
            >
              🧹 Clear
            </button>

            <button
              className="new-chat-btn"
              onClick={handleNewChat}
              disabled={isLoading}
            >
              ＋ New Chat
            </button>
          </div>
        </header>

        {/* ── Error banner ── */}
        {error && (
          <div className="error-banner" role="alert">
            <span>⚠️ {error}</span>
            <button className="error-dismiss" onClick={() => setError(null)}>
              ✕
            </button>
          </div>
        )}

        {/* ── Chat messages area ── */}
        <main className="app-main">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSelectPrompt={handleSendMessage}
          />
        </main>

        {/* ── Chat input footer ── */}
        <footer className="app-footer">
          {conversationId && (
            <div className="conv-id-bar">
              <span>🔑 Session: {conversationId.slice(0, 8)}…</span>
              <span className="conv-hint">Memory window: 10 messages</span>
            </div>
          )}
          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            isDisabled={!conversationId}
          />
        </footer>
      </div>
    </div>
  );
}
