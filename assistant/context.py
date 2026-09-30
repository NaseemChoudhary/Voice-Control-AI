"""Conversation context management."""

from ai import provider


def load_context():
    """Load the current conversation context."""
    return provider.load_history()


def clear_context():
    """Clear the conversation context."""
    provider.new_chat()


def add_context(user_message, assistant_message):
    """Add a message pair to the conversation context."""
    history = load_context()
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_message})
    provider.save_history(history)