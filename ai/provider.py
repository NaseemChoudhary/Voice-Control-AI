import json
import logging

import config

from google import genai
from groq import Groq


logger = logging.getLogger(__name__)
gemini_client = genai.Client(api_key=config.GEMINI_API_KEY) if config.GEMINI_API_KEY else None
groq_client = Groq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None


def load_history():
    """Load conversation history from JSON file."""
    try:
        with config.HISTORY_FILE.open("r", encoding="utf-8") as history_file:
            history = json.load(history_file)
        if not isinstance(history, list):
            raise ValueError("Conversation history must be a JSON list")
        return [
            item for item in history
            if isinstance(item, dict)
            and item.get("role") in ("user", "assistant")
            and isinstance(item.get("content"), str)
        ]
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("Could not load conversation history: %s", exc)
        return []


def save_history(history):
    """Save conversation history to JSON file."""
    config.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with config.HISTORY_FILE.open("w", encoding="utf-8") as history_file:
        json.dump(history, history_file, indent=4)


def new_chat():
    """Clear the conversation history."""
    try:
        config.HISTORY_FILE.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        logger.exception("Could not clear conversation history")
        raise


def _call_gemini(messages, system_instruction):
    """Call Gemini with the same conversation turns used by Groq."""
    if not gemini_client:
        raise RuntimeError("Gemini is not configured: GEMINI_API_KEY is missing")
    response = gemini_client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[
            {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [{"text": message["content"]}],
            }
            for message in messages
            if message["role"] in ("user", "assistant")
        ],
        config={"system_instruction": system_instruction},
    )
    return response.text


def _call_groq(messages):
    """Call Groq model as fallback."""
    if not groq_client:
        raise RuntimeError("Groq is not configured: GROQ_API_KEY is missing")
    response = groq_client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=messages
    )
    return response.choices[0].message.content


def ask_ai(prompt: str, history=None):
    """Ask AI a question, with Gemini primary and Groq fallback."""
    if history is None:
        history = load_history()

    system_instruction = (
        "Provide a concise, short summary response."
        if "in detail" not in prompt.lower()
        else "Provide a detailed, comprehensive response."
    )

    messages = [{"role": "system", "content": system_instruction}]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": prompt})

    response_text = None

    # Try Gemini First
    try:
        response_text = _call_gemini(messages, system_instruction)
        if not response_text:
            raise RuntimeError("Gemini returned an empty response")
    except Exception:
        logger.exception("Gemini request failed; trying Groq fallback")

    # Fallback to Groq if Gemini fails
    if not response_text:
        try:
            response_text = _call_groq(messages)
            if not response_text:
                raise RuntimeError("Groq returned an empty response")
        except Exception:
            logger.exception("Groq request failed")

    if not response_text:
        return "Sorry, all AI services are currently unavailable."

    # Save state
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response_text})
    try:
        save_history(history)
    except OSError:
        logger.exception("Could not persist conversation history")

    return response_text