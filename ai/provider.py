import os
import json
from dotenv import load_dotenv

load_dotenv()

from google import genai
from groq import Groq

HISTORY_FILE = "data/chat_history.json"

gemini_key = os.getenv("GEMINI_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None
groq_client = Groq(api_key=groq_key) if groq_key else None


def load_history():
    """Load conversation history from JSON file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(history):
    """Save conversation history to JSON file."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)


def new_chat():
    """Clear the conversation history."""
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)


def _call_gemini(messages, system_instruction):
    """Call Gemini with the same conversation turns used by Groq."""
    if not gemini_client:
        raise ValueError("GEMINI_API_KEY is missing from .env")
    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash",
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
        raise ValueError("GROQ_API_KEY is missing from .env")
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )
    return response.choices[0].message.content


def ask_ai(prompt: str, history=None, debug: bool = False):
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
    except Exception as e:
        if debug:
            print(f"[AI Debug] Gemini failed: {e}")

    # Fallback to Groq if Gemini fails
    if not response_text:
        try:
            response_text = _call_groq(messages)
        except Exception as e:
            if debug:
                print(f"[AI Debug] Groq failed: {e}")

    if not response_text:
        return "Sorry, all AI services are currently unavailable."

    # Save state
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response_text})
    save_history(history)

    return response_text