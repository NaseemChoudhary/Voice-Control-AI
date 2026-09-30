import speech_recognition as sr
import time

recognizer = sr.Recognizer()

# Your microphone:
# card 0, device 0 -> CX20724 Analog
MICROPHONE_INDEX = 0


def setup_microphone():
    """Initialize and calibrate the microphone once."""

    try:
        mic = sr.Microphone(device_index=MICROPHONE_INDEX)

        print("Initializing microphone...")

        with mic as source:
            print("Calibrating microphone...")
            recognizer.adjust_for_ambient_noise(
                source,
                duration=1
            )

        print("Microphone ready.")

        # Prevent Jarvis from waiting too long for speech
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        return mic

    except Exception as e:
        print("Microphone initialization error:", e)
        return None


def listen(mic, timeout=15, phrase_time_limit=5):
    """Listen to microphone and return recognized speech."""

    try:
        with mic as source:
            print("Listening...")

            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit
            )

        print("Recognizing...")

        text = recognizer.recognize_google(
            audio,
            language="en-IN"
        )

        print("You:", text)

        return text.lower()

    except sr.WaitTimeoutError:
        print("No speech detected.")
        return None

    except sr.UnknownValueError:
        print("Sorry, I couldn't understand.")
        return None

    except sr.RequestError as e:
        print("Google Speech Recognition error:", e)
        return None

    except Exception as e:
        print("Speech error:", e)
        return None