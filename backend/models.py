# models.py
# Pydantic models for request/response validation.
# Pydantic ensures incoming data has the correct types before we use it.

from typing import List, Dict, Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """
    Login payload containing username and password.
    """
    username: str
    password: str


class LoginResponse(BaseModel):
    """
    Response returned upon successful authentication.
    """
    username: str
    token: str
    message: str


class ChatRequest(BaseModel):
    """
    Data expected from the frontend when the user sends a message.
    - conversation_id: Which conversation this message belongs to.
    - message: The text the user typed.
    """
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    """
    Data sent back to the frontend after Gemini replies.
    - conversation_id: Echoed back so the frontend knows which chat this belongs to.
    - response: The AI-generated reply text.
    - turn_count: How many messages are in this conversation so far.
    """
    conversation_id: str
    response: str
    turn_count: int


class NewChatRequest(BaseModel):
    """
    Optional payload when initiating a new conversation.
    """
    username: Optional[str] = "guest"
    title: Optional[str] = "New Chat"


class NewChatResponse(BaseModel):
    """
    Data returned when the user creates a new conversation.
    - conversation_id: A fresh unique ID the frontend should store and use.
    - message: A human-friendly confirmation string.
    - title: Initial conversation title.
    """
    conversation_id: str
    message: str
    title: Optional[str] = "New Chat"


class HealthResponse(BaseModel):
    """
    Simple health-check payload so the frontend can confirm the backend is alive.
    """
    status: str
    message: str


class ConversationStatsResponse(BaseModel):
    """
    Metadata about an active conversation session.
    """
    model_config = {"protected_namespaces": ()}

    conversation_id: str
    total_messages: int
    user_turns: int
    ai_turns: int
    context_window_size: int


class ConversationItem(BaseModel):
    """
    Single conversation summary for the sidebar list.
    """
    conversation_id: str
    title: str
    username: str
    created_at: str
    updated_at: str


class ConversationDetailResponse(BaseModel):
    """
    Full conversation payload returned when a user clicks a chat in the sidebar.
    """
    conversation_id: str
    title: str
    messages: List[Dict[str, str]]
