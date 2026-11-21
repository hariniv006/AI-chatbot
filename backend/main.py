# main.py
# Entry point for the FastAPI backend server.
# Responsibilities:
#   - Load environment variables from .env
#   - Define API routes (/chat, /new-chat, /health)
#   - Configure CORS so the React frontend can call the API
#   - Handle and return meaningful, beginner-friendly errors for Gemini API calls

import os
import uuid
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Always load .env from the project root with override=True
env_root = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_root):
    load_dotenv(env_root, override=True)
else:
    load_dotenv(override=True)

import memory
import chatbot
from models import (
    ChatRequest,
    ChatResponse,
    NewChatRequest,
    NewChatResponse,
    HealthResponse,
    ConversationStatsResponse,
    LoginRequest,
    LoginResponse,
    ConversationItem,
    ConversationDetailResponse,
)

# -----------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------
# APP LIFECYCLE
# -----------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log startup and shutdown messages."""
    logger.info("🚀 Chatbot backend starting up with Google Gemini integration …")
    yield
    logger.info("🛑 Chatbot backend shutting down …")


# -----------------------------------------------------------------
# FASTAPI APP
# -----------------------------------------------------------------

app = FastAPI(
    title="Context-Aware AI Chatbot",
    description="A beginner-friendly chatbot powered by Google Gemini with conversation memory.",
    version="1.0.0",
    lifespan=lifespan,
)

# -----------------------------------------------------------------
# CORS CONFIGURATION
# -----------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server default
        "http://localhost:3000",   # Create-React-App default (fallback)
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],    # Allow GET, POST, OPTIONS, etc.
    allow_headers=["*"],    # Allow Content-Type, Authorization, etc.
)


# -----------------------------------------------------------------
# ROUTES
# -----------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """
    GET /health
    Quick check to verify the server is running.
    The frontend calls this on startup to give the user immediate feedback.
    """
    return HealthResponse(status="ok", message="Chatbot backend is running! 🟢")


@app.post("/login", response_model=LoginResponse, tags=["Auth"])
def login(request: LoginRequest):
    """
    POST /login
    Authenticate user. Supports demo credentials or any non-empty username.
    """
    username = request.username.strip()
    password = request.password.strip()

    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail="Username and password are required."
        )

    if len(password) < 4:
        raise HTTPException(
            status_code=401,
            detail="Password must be at least 4 characters long."
        )

    token = f"token-{uuid.uuid4().hex[:16]}"
    logger.info("User logged in: %s", username)

    return LoginResponse(
        username=username,
        token=token,
        message=f"Welcome, {username}! You are now logged in."
    )


@app.post("/new-chat", response_model=NewChatResponse, tags=["Conversation"])
def new_chat(request: Optional[NewChatRequest] = None):
    """
    POST /new-chat
    Generate a fresh conversation ID and register it in memory.
    The frontend stores this ID and sends it with every subsequent /chat request
    so the backend knows which conversation history to use.
    """
    conversation_id = str(uuid.uuid4())
    username = request.username if request and request.username else "guest"
    title = request.title if request and request.title else "New Chat"

    memory.create_conversation(conversation_id, username=username, title=title)

    logger.info("New conversation created: %s for user: %s", conversation_id, username)

    return NewChatResponse(
        conversation_id=conversation_id,
        message="New conversation started. Say hello! 👋",
        title=title,
    )


@app.get("/conversations", response_model=List[ConversationItem], tags=["Conversation"])
def list_conversations(username: str = "guest"):
    """
    GET /conversations?username=...
    Retrieve all conversations for the given user, ordered newest first.
    """
    conversations = memory.get_user_conversations(username)
    return conversations


@app.get("/chat/{conversation_id}", response_model=ConversationDetailResponse, tags=["Conversation"])
def get_chat_detail(conversation_id: str):
    """
    GET /chat/{conversation_id}
    Retrieve full message history and metadata for a conversation session.
    """
    if not memory.conversation_exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail=f"Conversation '{conversation_id}' not found."
        )

    meta = memory.get_conversation_metadata(conversation_id) or {}
    title = meta.get("title", "Chat")
    messages = memory.get_full_messages(conversation_id)

    return ConversationDetailResponse(
        conversation_id=conversation_id,
        title=title,
        messages=messages,
    )


@app.delete("/conversations/{conversation_id}", tags=["Conversation"])
def delete_conversation(conversation_id: str):
    """
    DELETE /conversations/{conversation_id}
    Completely remove conversation and its metadata from sidebar history.
    """
    if not memory.conversation_exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail=f"Conversation '{conversation_id}' not found."
        )

    memory.delete_conversation(conversation_id)
    logger.info("Deleted conversation: %s", conversation_id)
    return {"message": "Conversation deleted successfully", "conversation_id": conversation_id}


@app.post("/chat", response_model=ChatResponse, tags=["Conversation"])
def chat(request: ChatRequest):
    """
    POST /chat
    Main endpoint: accepts a user message, passes context to Google Gemini,
    and returns the AI's reply.

    Includes comprehensive, user-friendly error handling for:
    - Empty or whitespace-only messages (HTTP 400)
    - Unknown conversation IDs (HTTP 404)
    - Missing or invalid API key (HTTP 500 / 401)
    - Free tier quota & rate limits (HTTP 429)
    - Temporary high demand / server overload (HTTP 503)
    - Network connection errors or timeouts (HTTP 503)
    """

    # --- Validate: message must not be blank ---
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty. Please type something!"
        )

    # --- Validate: conversation must exist in memory ---
    if not memory.conversation_exists(request.conversation_id):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Conversation '{request.conversation_id}' not found. "
                "Please create a new conversation first by calling POST /new-chat."
            )
        )

    logger.info(
        "Chat request | conv=%s | message='%s'",
        request.conversation_id[:8] + "…",
        request.message[:60]
    )

    try:
        # Call chatbot logic using Google Gemini API
        ai_response = chatbot.get_ai_response(
            conversation_id=request.conversation_id,
            user_message=request.message.strip()
        )

    except ValueError as e:
        # Raised when GEMINI_API_KEY is missing or unconfigured
        logger.error("Configuration error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    except Exception as e:
        error_msg = str(e)
        error_lower = error_msg.lower()
        logger.error("Gemini API error: %s", error_msg)

        # 1. Invalid API Key
        if (
            "api_key_invalid" in error_lower
            or "api key not valid" in error_lower
            or ("invalid" in error_lower and "key" in error_lower)
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid Gemini API key. Please check your GEMINI_API_KEY in the .env file."
            )

        # 2. Quota & Rate Limit (HTTP 429)
        elif (
            "429" in error_msg
            or "resource_exhausted" in error_lower
            or "quota" in error_lower
            or "rate" in error_lower
        ):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini free-tier quota reached. The free tier allows ~15 requests per minute. "
                    "Please wait about 60 seconds and try again, or check your quota in Google AI Studio."
                )
            )

        # 3. Model Overload / Temporarily Unavailable (HTTP 503)
        elif "503" in error_msg or "unavailable" in error_lower:
            raise HTTPException(
                status_code=503,
                detail="The Gemini service is temporarily overloaded or experiencing high demand. Please try again in a moment."
            )

        # 4. Model Not Found (HTTP 404)
        elif "404" in error_msg or "not_found" in error_lower:
            model = chatbot._get_model()
            raise HTTPException(
                status_code=404,
                detail=f"The requested Gemini model '{model}' was not found. Please verify GEMINI_MODEL in your .env file (e.g. gemini-1.5-flash)."
            )

        # 5. Network / Timeout Errors
        elif "timeout" in error_lower or "connection" in error_lower or "network" in error_lower:
            raise HTTPException(
                status_code=503,
                detail="Network error connecting to Gemini. Please check your internet connection."
            )

        # 6. Fallback
        else:
            raise HTTPException(
                status_code=503,
                detail=f"AI service error: {error_msg}"
            )

    turn_count = memory.get_turn_count(request.conversation_id)

    logger.info(
        "Chat response | conv=%s | turns=%d | reply_len=%d chars",
        request.conversation_id[:8] + "…",
        turn_count,
        len(ai_response)
    )

    return ChatResponse(
        conversation_id=request.conversation_id,
        response=ai_response,
        turn_count=turn_count
    )


@app.get("/chat/{conversation_id}/stats", response_model=ConversationStatsResponse, tags=["Conversation"])
def get_conversation_stats(conversation_id: str):
    """
    GET /chat/{conversation_id}/stats
    Retrieve conversation metadata, turn counts, and context window size.
    """
    if not memory.conversation_exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail=f"Conversation '{conversation_id}' not found."
        )

    history = memory.get_full_messages(conversation_id)
    user_turns = sum(1 for m in history if m.get("role") == "user")
    ai_turns = sum(1 for m in history if m.get("role") in ("model", "assistant"))

    return ConversationStatsResponse(
        conversation_id=conversation_id,
        total_messages=len(history),
        user_turns=user_turns,
        ai_turns=ai_turns,
        context_window_size=memory.MAX_CONTEXT_MESSAGES,
    )


@app.delete("/chat/{conversation_id}", tags=["Conversation"])
def clear_conversation(conversation_id: str):
    """
    DELETE /chat/{conversation_id}
    Clear in-memory conversation history while retaining the session ID.
    """
    if not memory.conversation_exists(conversation_id):
        raise HTTPException(
            status_code=404,
            detail=f"Conversation '{conversation_id}' not found."
        )

    memory.clear_conversation(conversation_id)
    logger.info("Cleared conversation history for: %s", conversation_id)
    return {"message": "Conversation history cleared successfully", "conversation_id": conversation_id}
