import os
import subprocess

def shutdown():
    """Shutdown the assistant."""
    return "Shutting down."

def open_text_terminal():
    """Open a terminal window for text-based commands."""
    text_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "TextCommands.py"
    )

    subprocess.Popen([
        "gnome-terminal",
        "--",
        "python3",
        text_file
    ])
