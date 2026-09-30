import webbrowser

def open_google():
    """Open Google in the default browser."""
    webbrowser.open("https://www.google.com")
    return "Opening Google."


def search_web(query):
    """Search the web for the given query."""
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searching for {query}."