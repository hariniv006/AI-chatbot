# tests/test_chatbot.py
# A self-contained test suite for the Context-Aware AI Chatbot backend (Google Gemini API).
#
# HOW TO RUN (PowerShell, from the project root):
#   cd context-aware-ai-chatbot
#   .\.venv\Scripts\Activate.ps1          # activate virtual environment
#   pip install pytest httpx              # install test dependencies
#   pytest tests/test_chatbot.py -v       # run all tests
#
# NOTE: Tests that call the REAL Gemini API require a valid GEMINI_API_KEY
# in your .env file and an internet connection.
# Those integration tests are marked with @pytest.mark.skipif and
# are skipped automatically when the key is missing.
#
# Tests that do NOT call Gemini (memory, validation, new-chat, health, etc.)
# run fully offline without any API key or network required.

import os
import sys
import pytest

# Make sure Python can find the backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Fixtures ──────────────────────────────────────────────────────────────────

from fastapi.testclient import TestClient
import memory as mem
from main import app


@pytest.fixture(autouse=True)
def reset_memory():
    """
    Clear all in-memory conversation data before each test so tests are
    fully independent and cannot accidentally share state.
    """
    mem._conversation_store.clear()
    yield
    mem._conversation_store.clear()


@pytest.fixture
def client():
    """Return a synchronous TestClient for the FastAPI app."""
    return TestClient(app)


def has_api_key():
    """Return True if a real Gemini API key is configured."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(key) and key != "your_gemini_api_key_here" and not key.startswith("your_")


# ── Helper ────────────────────────────────────────────────────────────────────

def new_conversation(client):
    """Create a new conversation and return its ID."""
    resp = client.post("/new-chat")
    assert resp.status_code == 200
    return resp.json()["conversation_id"]


# =============================================================================
# TEST 1 – Health check
# =============================================================================
class TestHealth:
    def test_health_returns_ok(self, client):
        """GET /health must return status=ok."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "message" in body


# =============================================================================
# TEST 2 – New chat
# =============================================================================
class TestNewChat:
    def test_new_chat_creates_conversation(self, client):
        """POST /new-chat should return a non-empty conversation_id."""
        resp = client.post("/new-chat")
        assert resp.status_code == 200
        body = resp.json()
        assert "conversation_id" in body
        assert len(body["conversation_id"]) > 0
        assert "message" in body

    def test_new_chat_conversation_exists_in_memory(self, client):
        """After /new-chat the ID must be registered in the memory store."""
        resp = client.post("/new-chat")
        conv_id = resp.json()["conversation_id"]
        assert mem.conversation_exists(conv_id)

    def test_multiple_new_chats_get_unique_ids(self, client):
        """Each /new-chat call should return a distinct, unique ID."""
        ids = {client.post("/new-chat").json()["conversation_id"] for _ in range(5)}
        assert len(ids) == 5

    def test_new_chat_with_username_and_title(self, client):
        """POST /new-chat with custom username and title."""
        resp = client.post("/new-chat", json={"username": "alice", "title": "Python Help"})
        assert resp.status_code == 200
        data = resp.json()
        assert "conversation_id" in data
        assert data["title"] == "Python Help"


# =============================================================================
# TEST 2B – Authentication and Conversation History
# =============================================================================
class TestAuthAndHistory:
    def test_login_success(self, client):
        """POST /login with valid credentials should succeed."""
        resp = client.post("/login", json={"username": "alice", "password": "password123"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "alice"
        assert "token" in body
        assert "Welcome" in body["message"]

    def test_login_validation_errors(self, client):
        """POST /login with invalid/empty fields should return 400 or 401."""
        resp1 = client.post("/login", json={"username": "", "password": "123"})
        assert resp1.status_code == 400

        resp2 = client.post("/login", json={"username": "alice", "password": "12"})
        assert resp2.status_code == 401

    def test_conversations_sidebar_workflow(self, client):
        """Test creating chat, retrieving user conversations, getting detail, and deleting."""
        # 1. Create chat for user 'bob'
        resp_new = client.post("/new-chat", json={"username": "bob", "title": "Bob's Chat"})
        conv_id = resp_new.json()["conversation_id"]

        # 2. Add message to it
        mem.add_message(conv_id, "user", "What is an API?")
        mem.add_message(conv_id, "assistant", "An API is an Application Programming Interface.")

        # 3. Retrieve conversations for 'bob'
        resp_list = client.get("/conversations?username=bob")
        assert resp_list.status_code == 200
        convs = resp_list.json()
        assert len(convs) >= 1
        assert any(c["conversation_id"] == conv_id for c in convs)

        # 4. Retrieve detail for conv_id
        resp_detail = client.get(f"/chat/{conv_id}")
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        assert detail["conversation_id"] == conv_id
        assert len(detail["messages"]) == 2

        # 5. Delete conversation
        resp_del = client.delete(f"/conversations/{conv_id}")
        assert resp_del.status_code == 200
        assert not mem.conversation_exists(conv_id)


# =============================================================================
# TEST 3 – Input validation (no API key needed)
# =============================================================================
class TestInputValidation:
    def test_empty_message_rejected(self, client):
        """An empty message should return HTTP 400."""
        conv_id = new_conversation(client)
        resp = client.post("/chat", json={"conversation_id": conv_id, "message": ""})
        assert resp.status_code == 400

    def test_whitespace_only_message_rejected(self, client):
        """A whitespace-only message should return HTTP 400."""
        conv_id = new_conversation(client)
        resp = client.post("/chat", json={"conversation_id": conv_id, "message": "   "})
        assert resp.status_code == 400

    def test_unknown_conversation_id_returns_404(self, client):
        """Posting to a non-existent conversation_id should return HTTP 404."""
        resp = client.post(
            "/chat",
            json={"conversation_id": "does-not-exist", "message": "hello"}
        )
        assert resp.status_code == 404


# =============================================================================
# TEST 4 – Memory module (unit tests, offline)
# =============================================================================
class TestMemory:
    def test_create_and_exists(self):
        mem.create_conversation("test-1")
        assert mem.conversation_exists("test-1")

    def test_add_and_retrieve_messages(self):
        mem.create_conversation("test-2")
        mem.add_message("test-2", "user", "Hello")
        mem.add_message("test-2", "model", "Hi there!")
        ctx = mem.get_context_messages("test-2")
        assert len(ctx) == 2
        assert ctx[0]["role"] == "user"
        assert ctx[1]["role"] == "model"

    def test_turn_count_increments(self):
        mem.create_conversation("test-3")
        mem.add_message("test-3", "user", "msg 1")
        mem.add_message("test-3", "model", "reply 1")
        assert mem.get_turn_count("test-3") == 2

    def test_context_window_truncation(self):
        """
        If we add more than MAX_CONTEXT_MESSAGES, the returned window
        should be capped at that limit and keep the most recent messages.
        """
        mem.create_conversation("test-4")
        limit = mem.MAX_CONTEXT_MESSAGES

        # Add messages beyond the context limit
        for i in range(limit + 4):
            role = "user" if i % 2 == 0 else "model"
            mem.add_message("test-4", role, f"message {i}")

        ctx = mem.get_context_messages("test-4")
        assert len(ctx) == limit  # must be capped

        # Must be the LATEST messages, not the oldest
        total = mem.get_turn_count("test-4")
        assert ctx[-1]["text"] == f"message {total - 1}"

    def test_separate_conversations_dont_share_history(self):
        """
        Messages added to conversation A must not appear in conversation B.
        """
        mem.create_conversation("conv-A")
        mem.create_conversation("conv-B")
        mem.add_message("conv-A", "user", "Secret message in A")

        ctx_b = mem.get_context_messages("conv-B")
        assert ctx_b == []  # B should be completely empty

    def test_clear_conversation(self):
        mem.create_conversation("test-5")
        mem.add_message("test-5", "user", "hi")
        mem.clear_conversation("test-5")
        assert mem.get_turn_count("test-5") == 0

    def test_unknown_conversation_returns_empty(self):
        ctx = mem.get_context_messages("nonexistent")
        assert ctx == []


# =============================================================================
# TEST 5 – API Key & Configuration validation
# =============================================================================
class TestApiKeyValidation:
    def test_invalid_api_key_returns_error(self, client):
        """
        If GEMINI_API_KEY is invalid, backend returns HTTP 401 or appropriate error.
        """
        original_key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "AIzaSy_invalid_test_key_123456789"

        conv_id = new_conversation(client)
        resp = client.post(
            "/chat",
            json={"conversation_id": conv_id, "message": "Hello"}
        )

        # Restore original key
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)

        assert resp.status_code in (401, 400, 403, 429, 500, 503)

    def test_missing_api_key_returns_500(self, client):
        """
        If GEMINI_API_KEY is missing/empty, backend returns HTTP 500 configuration error.
        """
        original_key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = ""

        conv_id = new_conversation(client)
        resp = client.post(
            "/chat",
            json={"conversation_id": conv_id, "message": "Hello"}
        )

        # Restore original key
        if original_key is not None:
            os.environ["GEMINI_API_KEY"] = original_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)

        assert resp.status_code == 500
        assert "GEMINI_API_KEY is not set" in resp.json().get("detail", "")


# =============================================================================
# TEST 6 – Live Integration tests (Require real GEMINI_API_KEY)
# =============================================================================

@pytest.mark.skipif(not has_api_key(), reason="GEMINI_API_KEY not configured – skipping live API tests")
class TestIntegration:

    def test_normal_response(self, client):
        """
        TC1: A normal chat message should return a non-empty AI response.
        """
        conv_id = new_conversation(client)
        resp = client.post(
            "/chat",
            json={"conversation_id": conv_id, "message": "What is Python in one sentence?"},
            timeout=30,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["response"]) > 0
        assert body["conversation_id"] == conv_id

    def test_multi_turn_memory_5_turns(self, client):
        """
        TC2: Five-turn conversation – the AI should remember context.
        """
        conv_id = new_conversation(client)
        messages = [
            "My name is Alex. Nice to meet you!",
            "What is a variable in programming?",
            "Can you write a short 1-line example storing my name in a variable?",
            "What is the data type of my name in that example?",
            "What was the first thing I told you about myself?",
        ]
        last_response = ""
        for msg in messages:
            resp = client.post(
                "/chat",
                json={"conversation_id": conv_id, "message": msg},
                timeout=30,
            )
            assert resp.status_code == 200
            last_response = resp.json()["response"]

        assert "alex" in last_response.lower(), (
            f"Expected the AI to remember the name 'Alex' across turns. Got: {last_response[:300]}"
        )

    def test_separate_conversation_histories(self, client):
        """
        TC3: Two simultaneous conversations must NOT share history.
        """
        conv_a = new_conversation(client)
        client.post(
            "/chat",
            json={"conversation_id": conv_a, "message": "My name is Bob."},
            timeout=30,
        )

        conv_b = new_conversation(client)
        resp_b = client.post(
            "/chat",
            json={
                "conversation_id": conv_b,
                "message": "Do you know my name? What have we talked about before?",
            },
            timeout=30,
        )
        assert resp_b.status_code == 200
        response_b = resp_b.json()["response"].lower()
        assert "bob" not in response_b, (
            f"Conversation B should not know about Bob from Conversation A. Response: {response_b[:300]}"
        )

    def test_new_chat_resets_history(self, client):
        """
        TC4: Starting a new chat creates fresh context.
        """
        conv_1 = new_conversation(client)
        client.post(
            "/chat",
            json={"conversation_id": conv_1, "message": "Remember: the secret word is pineapple."},
            timeout=30,
        )

        conv_2 = new_conversation(client)
        assert conv_2 != conv_1

        resp = client.post(
            "/chat",
            json={"conversation_id": conv_2, "message": "What is the secret word I told you?"},
            timeout=30,
        )
        assert resp.status_code == 200
        assert "pineapple" not in resp.json()["response"].lower(), (
            "New chat should not leak history from the previous conversation."
        )
