# chatbot.py
# Core chatbot logic: builds the prompt, calls Google Gemini API, and returns a reply.
# This module is intentionally kept separate from the web layer (main.py) so
# the same logic can be reused in a CLI, test suite, or other interfaces.

import os
import logging
from typing import List, Dict
from google import genai
from google.genai import types
from dotenv import load_dotenv

import memory
from prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _reload_env() -> None:
    """
    Ensure .env values are loaded from the project root if not already in environment.
    """
    if "GEMINI_API_KEY" not in os.environ:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
        else:
            load_dotenv()


def _get_client() -> genai.Client:
    """
    Create and return a Gemini API client using the official Google GenAI SDK.
    The API key is read from the GEMINI_API_KEY environment variable.
    Raises a clear error if the key is missing or unconfigured.
    """
    _reload_env()
    api_key = os.getenv("GEMINI_API_KEY", "").strip().strip("\"'")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Please add your free Gemini API key to your .env file and restart the server."
        )
    return genai.Client(api_key=api_key)


def _get_model() -> str:
    """
    Read the model identifier from GEMINI_MODEL in .env.
    Defaults to 'gemini-3.5-flash-lite' as requested.
    """
    _reload_env()
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip().strip("\"'")
    return model if model else "gemini-3.5-flash-lite"


def _build_contents(context_messages: List[Dict[str, str]]) -> List[types.Content]:
    """
    Convert stored message history into Gemini Content objects.

    Parameters
    ----------
    context_messages : list of {"role": "user"|"model"|"assistant", "text": "..."}

    Returns
    -------
    list of types.Content objects with role ('user' or 'model') and text parts
    """
    contents = []
    for msg in context_messages:
        # Standardize AI role: convert 'assistant' to Gemini's expected 'model' role
        role = "model" if msg.get("role") in ("model", "assistant") else "user"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg.get("text", ""))]
            )
        )
    return contents


def get_ai_response(conversation_id: str, user_message: str) -> str:
    """
    Send a user message to Google Gemini and return the AI's reply.

    Steps
    -----
    1. Store the new user message in memory.
    2. Retrieve the recent context window (truncated history).
    3. Build Gemini-compatible contents list.
    4. Call client.models.generate_content(...) with system instructions.
    5. Extract the generated reply text via response.text.
    6. Store the AI's reply in memory.
    7. Return the reply text.

    Parameters
    ----------
    conversation_id : str – identifies which conversation this belongs to
    user_message    : str – the text the user just typed
    """
    # --- Step 1: Persist the user's message ---
    memory.add_message(conversation_id, role="user", text=user_message)

    # --- Step 2: Get the truncated context window ---
    context_messages = memory.get_context_messages(conversation_id)

    # --- Step 3: Format conversation history for Gemini ---
    contents = _build_contents(context_messages)

    # --- Step 4: Get client and model name ---
    client = _get_client()
    model_name = _get_model()

    logger.info("Calling Gemini API with model: %s", model_name)

    # --- Step 5: Call Gemini API (with resilient fallback on 429 / 503) ---
    fallback_model = "gemini-1.5-flash-8b"
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=1024,
            )
        )
    except Exception as e:
        err_str = str(e).lower()
        # If rate-limited or overloaded and a distinct fallback is available, try fallback
        if ("429" in err_str or "quota" in err_str or "503" in err_str or "unavailable" in err_str) and model_name != fallback_model:
            logger.warning("Model %s hit limit/overload; trying fallback model %s ...", model_name, fallback_model)
            response = client.models.generate_content(
                model=fallback_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                    max_output_tokens=1024,
                )
            )
        else:
            raise

    # --- Step 6: Extract the generated text ---
    ai_reply = getattr(response, "text", None)

    if not ai_reply:
        ai_reply = "I apologize, but I could not generate a response. Please try again."

    # --- Step 7: Persist the assistant's reply ---
    memory.add_message(conversation_id, role="model", text=ai_reply)

    return ai_reply
