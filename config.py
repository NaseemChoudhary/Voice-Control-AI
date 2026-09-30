import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Assistant configuration
HISTORY_FILE = "data/chat_history.json"
DEFAULT_CITY = "Thane"
MICROPHONE_INDEX = 0

# Model configuration
GEMINI_MODEL = "gemini-3.5-flash"
GROQ_MODEL = "llama-3.1-8b-instant"

# Speech configuration
SPEECH_RATE = 170
SPEECH_VOLUME = 1.0

print("Config loaded.")