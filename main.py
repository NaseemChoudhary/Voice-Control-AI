import time
from commands.system import open_text_terminal
from voice.listener import setup_microphone, listen
from assistant.router import route_command
from voice.speaker import speak


def main():
    print("==============================")
    print("       JARVIS STARTING")
    print("==============================")

    print("Warming up...")
    time.sleep(1)

    speak("Initializing Jarvis.")

    # Start Text Mode
    try:
        open_text_terminal()
    except Exception as e:
        print("Could not open text terminal:", e)

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

                except Exception as e:
                    print("Command error:", e)

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

                    except Exception as e:
                        print("Command error:", e)

        else:

            print("Sleeping...")


if __name__ == "__main__":
    main()