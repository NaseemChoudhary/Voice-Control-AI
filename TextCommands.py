import os
import subprocess


def open_text_terminal():
    text_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "TextCommands.py"
    )

    subprocess.Popen([
        "gnome-terminal",
        "--",
        "python3",
        text_file
    ])


def text_command_loop():
    print("\n==============================")
    print("       JARVIS TEXT MODE")
    print("==============================")
    print("Type your command below.")
    print("Type 'bye' to exit text mode.\n")

    while True:
        command = input("You: ").strip()

        if not command:
            continue

        if command.lower() == "bye":
            print("Closing text mode...")
            break

        from assistant.router import route_command
        try:
            handled, message, continue_running = route_command(command)
            if message:
                print(message)
            if not continue_running:
                break
            if not handled:
                print("Command was not handled.")
        except Exception as e:
            print("Command error:", e)

if __name__ == "__main__":
    text_command_loop()