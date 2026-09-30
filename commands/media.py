import pywhatkit

def play_youtube(query):
    """Play a video on YouTube."""
    pywhatkit.playonyt(query)
    return f"Playing {query} on YouTube."