"""Intent classification for user commands."""

INTENT_NEW_CHAT = "new_chat"
INTENT_OPEN_GOOGLE = "open_google"
INTENT_PLAY = "play"
INTENT_NEWS = "news"
INTENT_SEARCH = "search"
INTENT_WEATHER = "weather"
INTENT_AI = "ai"
INTENT_SHUTDOWN = "shutdown"


def classify(command: str) -> str:
    """Classify a user command into an intent."""
    c = command.lower()

    if any(w in c for w in ["new chat", "clear memory", "forget conversation", "reset chat"]):
        return INTENT_NEW_CHAT
    if "open google" in c:
        return INTENT_OPEN_GOOGLE
    if "play" in c:
        return INTENT_PLAY
    if "news" in c:
        return INTENT_NEWS
    if "search" in c or ".com" in c:
        return INTENT_SEARCH
    if "weather" in c or "temperature" in c:
        return INTENT_WEATHER
    if "shutdown" in c:
        return INTENT_SHUTDOWN

    return INTENT_AI