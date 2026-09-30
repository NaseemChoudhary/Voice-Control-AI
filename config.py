"""Application settings and logging configuration."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "chat_history.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
WEATHER_API_URL = os.getenv("WEATHER_API_URL", "https://api.weatherapi.com/v1/forecast.json")
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Thane")
MICROPHONE_INDEX = int(os.getenv("MICROPHONE_INDEX", "0"))
SPEECH_ENGINE = os.getenv("SPEECH_ENGINE", "espeak")
SPEECH_RATE = int(os.getenv("SPEECH_RATE", "170"))
SPEECH_VOLUME = float(os.getenv("SPEECH_VOLUME", "1.0"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def configure_logging():
    """Configure consistent console logging once for the application."""
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
