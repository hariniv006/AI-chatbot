// services/api.js
// All network calls to the FastAPI backend live here.
// Keeping API logic in one place means you only need to update the base URL
// or error handling logic in a single file.

const BASE_URL = "http://localhost:8000";

/**
 * Makes a fetch request and returns the parsed JSON body.
 * Throws a descriptive Error when the HTTP status is not OK (2xx).
 */
async function apiFetch(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`Server returned an unexpected response (HTTP ${response.status})`);
  }

  if (!response.ok) {
    const message = data?.detail || `HTTP error ${response.status}`;
    throw new Error(message);
  }

  return data;
}

/**
 * Check if the backend server is running.
 */
export async function checkHealth() {
  return apiFetch("/health");
}

/**
 * Log in with username and password.
 */
export async function loginUser(username, password) {
  return apiFetch("/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

/**
 * Ask the backend to create a new conversation and return its unique ID.
 */
export async function createNewChat(username = "guest", title = "New Chat") {
  return apiFetch("/new-chat", {
    method: "POST",
    body: JSON.stringify({ username, title }),
  });
}

/**
 * Fetch all conversations for a specific user to display in the sidebar.
 */
export async function getConversations(username = "guest") {
  return apiFetch(`/conversations?username=${encodeURIComponent(username)}`);
}

/**
 * Fetch full transcript and metadata for a conversation.
 */
export async function getChatDetail(conversationId) {
  return apiFetch(`/chat/${conversationId}`);
}

/**
 * Delete a conversation completely from the backend store.
 */
export async function deleteConversation(conversationId) {
  return apiFetch(`/conversations/${conversationId}`, { method: "DELETE" });
}

/**
 * Send a user message and receive the AI's reply.
 */
export async function sendMessage(conversationId, message) {
  return apiFetch("/chat", {
    method: "POST",
    body: JSON.stringify({
      conversation_id: conversationId,
      message: message,
    }),
  });
}

/**
 * Clear in-memory history for a specific conversation.
 */
export async function clearConversation(conversationId) {
  return apiFetch(`/chat/${conversationId}`, { method: "DELETE" });
}

/**
 * Get stats for an active conversation.
 */
export async function getConversationStats(conversationId) {
  return apiFetch(`/chat/${conversationId}/stats`);
}
