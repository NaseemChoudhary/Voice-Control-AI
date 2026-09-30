"""Route commands and return results without choosing how to present them."""

from commands import browser, media, weather, news, system
from ai import provider


def route_command(command: str):
    """Return (handled, message, continue_running) for a command."""
    from assistant.intent import classify

    intent = classify(command)

    if intent == "new_chat":
        provider.new_chat()
        return True, "Conversation cleared.", True
    if intent == "open_google":
        return True, browser.open_google(), True
    if intent == "play":
        query = command.lower().replace("play", "", 1).strip()
        if query:
            return True, media.play_youtube(query), True
        return True, "What would you like me to play?", True
    if intent == "news":
        headlines = news.get_top_news()
        if not headlines:
            return True, "Sorry, I was unable to fetch the news.", True
        return True, "Here are today's top headlines. " + " ".join(
            f"Headline {i}: {headline.replace('- BBC News', '').strip()}"
            for i, headline in enumerate(headlines[:5], start=1)
        ), True
    if intent == "search":
        return True, browser.search_web(command), True
    if intent == "weather":
        return True, weather.get_weather(command), True
    if intent == "shutdown":
        return True, system.shutdown(), False
    if intent == "ai":
        return True, provider.ask_ai(command), True
    return False, "", True
