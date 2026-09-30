"""Response generation and formatting."""

from ai import provider


def generate_response(prompt: str) -> str:
    """Generate a response for a given prompt."""
    return provider.ask_ai(prompt)


def format_response(text: str) -> str:
    """Format a response for output."""
    return str(text)