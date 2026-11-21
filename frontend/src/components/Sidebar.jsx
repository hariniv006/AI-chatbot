// components/Sidebar.jsx
// Sidebar component showing past chat history, active chat indicator,
// new chat action, and user profile with logout.

export default function Sidebar({
  conversations = [],
  activeId = null,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  currentUser,
  onLogout,
  isOpen = false,
  onClose,
}) {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} />}

      <aside className={`sidebar ${isOpen ? "sidebar--open" : ""}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <span className="sidebar-logo">🤖</span>
            <span className="sidebar-app-name">Lexi AI</span>
          </div>
          {onClose && (
            <button className="sidebar-close-btn" onClick={onClose} title="Close sidebar">
              ✕
            </button>
          )}
        </div>

        {/* New Chat Button */}
        <div className="sidebar-action-wrap">
          <button className="sidebar-new-chat-btn" onClick={onNewChat}>
            <span className="btn-icon">＋</span>
            <span>New Chat</span>
          </button>
        </div>

        {/* Conversation List */}
        <div className="sidebar-section-title">
          <span>CHAT HISTORY</span>
          <span className="history-count">{conversations.length}</span>
        </div>

        <div className="sidebar-list">
          {conversations.length === 0 ? (
            <div className="sidebar-empty">
              <span>No past chats yet.</span>
              <p>Start a conversation to see it listed here!</p>
            </div>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.conversation_id === activeId;
              return (
                <div
                  key={conv.conversation_id}
                  className={`sidebar-item ${isActive ? "sidebar-item--active" : ""}`}
                  onClick={() => {
                    onSelectConversation(conv.conversation_id);
                    if (onClose) onClose();
                  }}
                  title={conv.title}
                >
                  <span className="item-icon">💬</span>
                  <div className="item-content">
                    <span className="item-title">{conv.title || "New Chat"}</span>
                    <span className="item-time">{conv.updated_at || conv.created_at || ""}</span>
                  </div>
                  <button
                    className="item-delete-btn"
                    title="Delete chat"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conv.conversation_id);
                    }}
                  >
                    🗑️
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Sidebar Footer / User Profile */}
        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar">
              {(currentUser?.username || "U")[0].toUpperCase()}
            </div>
            <div className="user-details">
              <span className="username">{currentUser?.username || "Guest"}</span>
              <span className="user-status">Online 🟢</span>
            </div>
          </div>
          <button
            className="logout-btn"
            onClick={onLogout}
            title="Sign out of your account"
          >
            🚪 Logout
          </button>
        </div>
      </aside>
    </>
  );
}

