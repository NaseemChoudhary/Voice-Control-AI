"""Application settings and logging configuration."""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "chat_history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

try:
    with SETTINGS_FILE.open("r", encoding="utf-8") as settings_file:
        _saved_settings = json.load(settings_file)
    if not isinstance(_saved_settings, dict):
        _saved_settings = {}
except FileNotFoundError:
    _saved_settings = {}
except (OSError, json.JSONDecodeError):
    logging.getLogger(__name__).exception("Could not load saved settings")
    _saved_settings = {}


def _setting(name, default):
    return _saved_settings.get(name, default)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

GEMINI_MODEL = _setting("gemini_model", os.getenv("GEMINI_MODEL", "gemini-3.5-flash"))
GROQ_MODEL = _setting("groq_model", os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"))
WEATHER_API_URL = os.getenv("WEATHER_API_URL", "https://api.weatherapi.com/v1/forecast.json")
DEFAULT_CITY = _setting("default_city", os.getenv("DEFAULT_CITY", "Thane"))
MICROPHONE_INDEX = int(_setting("microphone_index", os.getenv("MICROPHONE_INDEX", "0")))
SPEECH_ENGINE = os.getenv("SPEECH_ENGINE", "espeak")
SPEECH_RATE = int(_setting("speech_rate", os.getenv("SPEECH_RATE", "170")))
SPEECH_VOLUME = float(_setting("speech_volume", os.getenv("SPEECH_VOLUME", "1.0")))
SPEECH_ENABLED = bool(_setting("speech_enabled", True))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def configure_logging():
    """Configure consistent console logging once for the application."""
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def save_settings(settings):
    """Persist UI-editable settings and update the active configuration."""
    global GEMINI_MODEL, GROQ_MODEL, DEFAULT_CITY, MICROPHONE_INDEX
    global SPEECH_RATE, SPEECH_VOLUME, SPEECH_ENABLED, _saved_settings
    allowed = {"gemini_model", "groq_model", "default_city", "microphone_index",
               "speech_rate", "speech_volume", "speech_enabled"}
    updated = {key: value for key, value in settings.items() if key in allowed}
    merged = {**_saved_settings, **updated}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_FILE.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as settings_file:
        json.dump(merged, settings_file, indent=2)
    temporary.replace(SETTINGS_FILE)
    _saved_settings = merged
    GEMINI_MODEL = str(merged.get("gemini_model", GEMINI_MODEL))
    GROQ_MODEL = str(merged.get("groq_model", GROQ_MODEL))
    DEFAULT_CITY = str(merged.get("default_city", DEFAULT_CITY))
    MICROPHONE_INDEX = int(merged.get("microphone_index", MICROPHONE_INDEX))
    SPEECH_RATE = int(merged.get("speech_rate", SPEECH_RATE))
    SPEECH_VOLUME = float(merged.get("speech_volume", SPEECH_VOLUME))
    SPEECH_ENABLED = bool(merged.get("speech_enabled", SPEECH_ENABLED))


def current_settings():
    return {
        "gemini_model": GEMINI_MODEL, "groq_model": GROQ_MODEL,
        "default_city": DEFAULT_CITY, "microphone_index": MICROPHONE_INDEX,
        "speech_rate": SPEECH_RATE, "speech_volume": SPEECH_VOLUME,
        "speech_enabled": SPEECH_ENABLED,
    }
