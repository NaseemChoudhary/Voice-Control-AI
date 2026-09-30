import logging
import time

from config import configure_logging
from commands.system import open_text_terminal
from voice.listener import setup_microphone, listen
from assistant.router import route_command
from voice.speaker import speak

logger = logging.getLogger(__name__)


def main():
    configure_logging()
    print("==============================")
    print("       JARVIS STARTING")
    print("==============================")

    print("Warming up...")
    time.sleep(1)

    speak("Initializing Jarvis.")

    # Start Text Mode
    try:
        open_text_terminal()
    except Exception:
        logger.exception("Could not open text terminal")

    # Initialize microphone ONCE
    microphone = setup_microphone()

    if microphone is None:
        speak("I could not access the microphone.")
        raise SystemExit

    running = True

    speak("I am ready.")

    # -----------------------------
    # Main Loop
    # -----------------------------

    while running:

        word = listen(
            microphone,
            timeout=15,
            phrase_time_limit=5
        )

        if not word:
            continue

        # -------------------------
        # Shutdown
        # -------------------------

        if "shutdown" in word:

            print("Shutting down...")
            speak("Shutting down.")

            running = False
            time.sleep(1)

            break

        # -------------------------
        # Wake Word
        # -------------------------

        if "jarvis" in word:

            command = word.replace(
                "jarvis",
                "",
                1
            ).strip()

            # Example:
            # "Jarvis open Google"
            if command:

                print("Command:", command)

                try:
                    handled, message, continue_loop = route_command(command)
                    if message:
                        print(message)
                        speak(message)
                    if not continue_loop:
                        running = False
                        break

                except Exception:
                    logger.exception("Command handling failed")
                    message = "Sorry, I couldn't complete that command."
                    print(message)
                    speak(message)

            # User only said "Jarvis"
            else:

                speak("I'm listening.")

                command = listen(
                    microphone,
                    timeout=10,
                    phrase_time_limit=8
                )

                if command:

                    try:
                        handled, message, continue_loop = route_command(command)
                        if message:
                            print(message)
                            speak(message)
                        if not continue_loop:
                            running = False
                            break

                    except Exception:
                        logger.exception("Command handling failed")
                        message = "Sorry, I couldn't complete that command."
                        print(message)
                        speak(message)

        else:

            print("Sleeping...")


if __name__ == "__main__":
    main()