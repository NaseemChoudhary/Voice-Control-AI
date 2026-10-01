"""Terminal interface backed by the shared assistant controller."""

import logging

import config
from assistant.controller import AssistantController

logger = logging.getLogger(__name__)


def run_cli():
    config.configure_logging()
    print("\n==============================")
    print("     JARVIS TERMINAL MODE")
    print("==============================")
    print("Say 'Jarvis' followed by a command, or type a command. Type 'bye' to exit.\n")

    def display_event(event):
        if event.get("type") == "transcription":
            print(f"You (voice): {event['text']}")
        elif event.get("type") == "message" and event.get("role") == "assistant":
            print(f"JARVIS: {event['text']}\n")
        elif event.get("type") == "status" and event.get("text") == "Microphone unavailable":
            print("Voice input unavailable; check microphone settings.")

    controller = AssistantController(display_event)
    controller.start_voice()
    try:
        while True:
            try:
                command = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nClosing JARVIS terminal mode.")
                break
            if not command:
                continue
            if command.lower() in {"bye", "exit", "quit"}:
                print("Closing JARVIS terminal mode.")
                break
            try:
                if controller.execute(command, source="cli") is False:
                    break
            except Exception:
                logger.exception("CLI command failed")
                print("JARVIS: Sorry, I couldn't complete that command.\n")
    finally:
        controller.stop_voice()
