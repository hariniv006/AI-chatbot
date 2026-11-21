# memory.py
# Manages conversation history and metadata in memory using Python dictionaries.
# Each conversation_id maps to its own list of messages and metadata (title, username, timestamps).

import os
from datetime import datetime
from typing import List, Dict, Optional

# -----------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------

# Maximum number of recent messages to keep in context (e.g. 10 = 5 turns).
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))

# -----------------------------------------------------------------
# IN-MEMORY STORE
# -----------------------------------------------------------------

# Format: { "conv-id-123": [ {"role": "user", "text": "...", "timestamp": "..."}, ... ] }
_conversation_store: Dict[str, List[Dict[str, str]]] = {}

# Format: { "conv-id-123": {"conversation_id": "...", "title": "...", "username": "...", "updated_at": "..."} }
_conversation_metadata: Dict[str, Dict] = {}


# -----------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------

def create_conversation(conversation_id: str, username: str = "guest", title: str = "New Chat") -> None:
    """
    Initialise an empty history list and metadata for a brand-new conversation.
    """
    if conversation_id not in _conversation_store:
        _conversation_store[conversation_id] = []
        _conversation_metadata[conversation_id] = {
            "conversation_id": conversation_id,
            "title": title,
            "username": username,
            "created_at": datetime.now().strftime("%I:%M %p"),
            "updated_at": datetime.now().strftime("%I:%M %p"),
        }


def conversation_exists(conversation_id: str) -> bool:
    """Return True if we already have history for this conversation ID."""
    return conversation_id in _conversation_store


def add_message(conversation_id: str, role: str, text: str) -> None:
    """
    Append one message to a conversation's history and update metadata.
    Automatically assigns a friendly title from the first user message.
    """
    if conversation_id not in _conversation_store:
        create_conversation(conversation_id)

    timestamp = datetime.now().strftime("%I:%M %p")
    _conversation_store[conversation_id].append({
        "role": role,
        "text": text,
        "timestamp": timestamp,
    })

    # Update metadata
    if conversation_id in _conversation_metadata:
        _conversation_metadata[conversation_id]["updated_at"] = timestamp
        # If title is still generic and this is a user message, generate title
        if role == "user" and _conversation_metadata[conversation_id]["title"] == "New Chat":
            clean_title = text.strip().replace("\n", " ")
            _conversation_metadata[conversation_id]["title"] = (
                clean_title[:32] + "…" if len(clean_title) > 32 else clean_title
            )


def get_context_messages(conversation_id: str) -> List[Dict[str, str]]:
    """
    Return the most recent MAX_CONTEXT_MESSAGES messages for a conversation.
    """
    if conversation_id not in _conversation_store:
        return []

    history = _conversation_store[conversation_id]
    return history[-MAX_CONTEXT_MESSAGES:]


def get_full_messages(conversation_id: str) -> List[Dict[str, str]]:
    """
    Return all messages for a conversation session.
    """
    return _conversation_store.get(conversation_id, [])


def get_turn_count(conversation_id: str) -> int:
    """Return the total number of messages stored for a conversation."""
    return len(_conversation_store.get(conversation_id, []))


def get_user_conversations(username: str = "guest") -> List[Dict]:
    """
    Return all conversations belonging to the given username, sorted newest first.
    """
    matching = [
        meta for meta in _conversation_metadata.values()
        if meta.get("username", "guest").lower() == username.lower()
    ]
    # Return reversed (newest first)
    return list(reversed(matching))


def get_conversation_metadata(conversation_id: str) -> Optional[Dict]:
    """Retrieve metadata dict for a conversation."""
    return _conversation_metadata.get(conversation_id)


def clear_conversation(conversation_id: str) -> None:
    """
    Delete message history for a conversation while retaining metadata.
    """
    if conversation_id in _conversation_store:
        _conversation_store[conversation_id] = []


def delete_conversation(conversation_id: str) -> None:
    """
    Completely remove a conversation and its metadata.
    """
    _conversation_store.pop(conversation_id, None)
    _conversation_metadata.pop(conversation_id, None)


def get_all_conversation_ids() -> List[str]:
    """Return all active conversation IDs."""
    return list(_conversation_store.keys())
