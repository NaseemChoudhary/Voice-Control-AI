import logging
import speech_recognition as sr

recognizer = sr.Recognizer()

from config import MICROPHONE_INDEX

logger = logging.getLogger(__name__)


def setup_microphone():
    """Initialize and calibrate the microphone once."""

    try:
        mic = sr.Microphone(device_index=MICROPHONE_INDEX)

        logger.info("Initializing microphone")

        with mic as source:
            logger.info("Calibrating microphone")
            recognizer.adjust_for_ambient_noise(
                source,
                duration=1
            )

        logger.info("Microphone ready")

        # Prevent Jarvis from waiting too long for speech
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        return mic

    except Exception:
        logger.exception("Microphone initialization failed")
        return None


def listen(mic, timeout=15, phrase_time_limit=5):
    """Listen to microphone and return recognized speech."""

    try:
        with mic as source:
            logger.debug("Listening for speech")

            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit
            )

        logger.debug("Recognizing speech")

        text = recognizer.recognize_google(
            audio,
            language="en-IN"
        )

        logger.info("Recognized user speech")

        return text.lower()

    except sr.WaitTimeoutError:
        logger.debug("No speech detected before timeout")
        return None
    except sr.UnknownValueError:
        logger.info("Speech could not be understood")
        return None
    except sr.RequestError:
        logger.exception("Speech recognition service request failed")
        return None
    except Exception:
        logger.exception("Unexpected speech recognition failure")
        return None