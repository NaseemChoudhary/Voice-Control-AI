"""Speech output adapter."""

import logging

import config

logger = logging.getLogger(__name__)
SPEECH_STATUS = "Not tested" if config.SPEECH_ENABLED else "Disabled"
_engine = None


def speak(text):
    """Speak text, logging speech engine failures without interrupting commands."""
    global _engine, SPEECH_STATUS
    if not config.SPEECH_ENABLED:
        SPEECH_STATUS = "Disabled"
        return
    try:
        import pyttsx3

        if _engine is None:
            _engine = pyttsx3.init(config.SPEECH_ENGINE)
        _engine.setProperty("rate", config.SPEECH_RATE)
        _engine.setProperty("volume", config.SPEECH_VOLUME)
        _engine.say(str(text))
        _engine.runAndWait()
        SPEECH_STATUS = "Ready"
    except Exception:
        SPEECH_STATUS = "Unavailable"
        logger.exception("Speech output failed")
