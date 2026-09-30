"""Speech output adapter."""

import logging

from config import SPEECH_ENGINE, SPEECH_RATE, SPEECH_VOLUME

logger = logging.getLogger(__name__)
_engine = None


def speak(text):
    """Speak text, logging speech engine failures without interrupting commands."""
    global _engine
    try:
        import pyttsx3

        if _engine is None:
            _engine = pyttsx3.init(SPEECH_ENGINE)
            _engine.setProperty("rate", SPEECH_RATE)
            _engine.setProperty("volume", SPEECH_VOLUME)
        _engine.say(str(text))
        _engine.runAndWait()
    except Exception:
        logger.exception("Speech output failed")
