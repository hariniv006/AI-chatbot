# memory.py
# Persistent conversation history and metadata manager using SQLite.
# Chats and message history persist automatically across server restarts.

import os
import time
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------

# Maximum number of recent messages to keep in context (e.g. 10 = 5 turns).
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))

# SQLite database path (persists in backend directory by default)
DB_PATH = os.getenv(
    "CHATBOT_DB_PATH",
    os.path.join(os.path.dirname(__file__), "chat_history.db")
)


# -----------------------------------------------------------------
# DATABASE SETUP
# -----------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    """Initialize database tables and indexes if they do not exist."""
    with _get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_at_epoch REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(username)")
        conn.commit()


# Initialize database schema on module import
_init_db()


# -----------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------

def create_conversation(
    conversation_id: str,
    username: str = "guest",
    title: str = "New Chat"
) -> None:
    """
    Initialise a conversation record in SQLite if it does not already exist.
    """
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    epoch = time.time()

    with _get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO conversations
            (conversation_id, username, title, created_at, updated_at, updated_at_epoch)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (conversation_id, username, title, time_str, time_str, epoch))
        conn.commit()


def conversation_exists(conversation_id: str) -> bool:
    """Return True if conversation exists in the database."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        )
        return cursor.fetchone() is not None


def add_message(conversation_id: str, role: str, text: str) -> None:
    """
    Append one message to conversation history in SQLite and update metadata.
    Automatically assigns a friendly title from the first user message.
    """
    if not conversation_exists(conversation_id):
        create_conversation(conversation_id)

    now = datetime.now()
    timestamp = now.strftime("%I:%M %p")
    epoch = time.time()

    with _get_connection() as conn:
        # Insert message
        conn.execute("""
            INSERT INTO messages (conversation_id, role, text, timestamp)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, role, text, timestamp))

        # Check existing title
        row = conn.execute(
            "SELECT title FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()

        current_title = row["title"] if row else "New Chat"

        # Auto-generate title from the first user question
        if role == "user" and current_title in ("New Chat", "", None):
            clean_title = text.strip().replace("\n", " ")
            new_title = clean_title[:32] + "…" if len(clean_title) > 32 else clean_title
            conn.execute("""
                UPDATE conversations
                SET title = ?, updated_at = ?, updated_at_epoch = ?
                WHERE conversation_id = ?
            """, (new_title, timestamp, epoch, conversation_id))
        else:
            conn.execute("""
                UPDATE conversations
                SET updated_at = ?, updated_at_epoch = ?
                WHERE conversation_id = ?
            """, (timestamp, epoch, conversation_id))

        conn.commit()


def get_context_messages(conversation_id: str) -> List[Dict[str, str]]:
    """
    Return the most recent MAX_CONTEXT_MESSAGES messages for a conversation.
    """
    with _get_connection() as conn:
        cursor = conn.execute("""
            SELECT role, text, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,))
        rows = cursor.fetchall()
        messages = [
            {"role": r["role"], "text": r["text"], "timestamp": r["timestamp"]}
            for r in rows
        ]
        return messages[-MAX_CONTEXT_MESSAGES:]


def get_full_messages(conversation_id: str) -> List[Dict[str, str]]:
    """
    Return all messages for a conversation session.
    """
    with _get_connection() as conn:
        cursor = conn.execute("""
            SELECT role, text, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,))
        return [
            {"role": r["role"], "text": r["text"], "timestamp": r["timestamp"]}
            for r in cursor.fetchall()
        ]


def get_turn_count(conversation_id: str) -> int:
    """Return the total number of messages stored for a conversation."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        row = cursor.fetchone()
        return row["cnt"] if row else 0


def get_user_conversations(username: str = "guest") -> List[Dict]:
    """
    Return all conversations belonging to the given username, sorted newest first.
    """
    with _get_connection() as conn:
        cursor = conn.execute("""
            SELECT conversation_id, title, username, created_at, updated_at
            FROM conversations
            WHERE LOWER(username) = LOWER(?)
            ORDER BY updated_at_epoch DESC
        """, (username,))
        return [
            {
                "conversation_id": r["conversation_id"],
                "title": r["title"],
                "username": r["username"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in cursor.fetchall()
        ]


def get_conversation_metadata(conversation_id: str) -> Optional[Dict]:
    """Retrieve metadata dict for a conversation."""
    with _get_connection() as conn:
        cursor = conn.execute("""
            SELECT conversation_id, title, username, created_at, updated_at
            FROM conversations
            WHERE conversation_id = ?
        """, (conversation_id,))
        r = cursor.fetchone()
        if not r:
            return None
        return {
            "conversation_id": r["conversation_id"],
            "title": r["title"],
            "username": r["username"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }


def clear_conversation(conversation_id: str) -> None:
    """
    Delete message history for a conversation while retaining metadata.
    """
    with _get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.commit()


def delete_conversation(conversation_id: str) -> None:
    """
    Completely remove a conversation and its messages.
    """
    with _get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
        conn.commit()


def get_all_conversation_ids() -> List[str]:
    """Return all active conversation IDs."""
    with _get_connection() as conn:
        cursor = conn.execute("SELECT conversation_id FROM conversations")
        return [r["conversation_id"] for r in cursor.fetchall()]


def clear_all() -> None:
    """Wipe all conversations and messages from database (useful for tests)."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM conversations")
        conn.commit()


# -----------------------------------------------------------------
# BACKWARD-COMPATIBLE DICT PROXIES
# -----------------------------------------------------------------
# Preserves legacy direct dict accesses (e.g. `_conversation_store.clear()`)
# in tests while routing everything to the persistent SQLite database.

class _ConversationStoreProxy:
    def clear(self):
        clear_all()

    def __contains__(self, conv_id):
        return conversation_exists(conv_id)

    def __getitem__(self, conv_id):
        if not conversation_exists(conv_id):
            raise KeyError(conv_id)
        return get_full_messages(conv_id)

    def get(self, conv_id, default=None):
        if conversation_exists(conv_id):
            return get_full_messages(conv_id)
        return default

    def keys(self):
        return get_all_conversation_ids()

    def pop(self, conv_id, default=None):
        if conversation_exists(conv_id):
            delete_conversation(conv_id)
            return []
        return default


class _ConversationMetadataProxy:
    def clear(self):
        clear_all()

    def __contains__(self, conv_id):
        return conversation_exists(conv_id)

    def __getitem__(self, conv_id):
        meta = get_conversation_metadata(conv_id)
        if meta is None:
            raise KeyError(conv_id)
        return meta

    def get(self, conv_id, default=None):
        meta = get_conversation_metadata(conv_id)
        return meta if meta is not None else default

    def values(self):
        with _get_connection() as conn:
            cursor = conn.execute("""
                SELECT conversation_id, title, username, created_at, updated_at
                FROM conversations
            """)
            return [
                {
                    "conversation_id": r["conversation_id"],
                    "title": r["title"],
                    "username": r["username"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
                for r in cursor.fetchall()
            ]


_conversation_store = _ConversationStoreProxy()
_conversation_metadata = _ConversationMetadataProxy()
