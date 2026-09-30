"""Terminal interface backed by the shared assistant controller."""

import logging

import config
from assistant.controller import AssistantController

logger = logging.getLogger(__name__)


def run_cli():
    config.configure_logging()
    print("\n==============================")
    print("       JARVIS TEXT MODE")
    print("==============================")
    print("Type a command below. Type 'bye' to exit.\n")

    def display_event(event):
        if event.get("type") == "message" and event.get("role") == "assistant":
            print(f"JARVIS: {event['text']}\n")

    controller = AssistantController(display_event)
    while True:
        try:
            command = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nClosing JARVIS text mode.")
            break
        if not command:
            continue
        if command.lower() in {"bye", "exit", "quit"}:
            print("Closing JARVIS text mode.")
            break
        try:
            if controller.execute(command, source="cli") is False:
                break
        except Exception:
            logger.exception("CLI command failed")
            print("JARVIS: Sorry, I couldn't complete that command.\n")
