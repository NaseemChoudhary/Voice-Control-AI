"""Response generation and formatting."""

from ai import provider


def generate_response(prompt: str, debug: bool = False) -> str:
    """Generate a response for a given prompt."""
    return provider.ask_ai(prompt, debug=debug)


def format_response(text: str) -> str:
    """Format a response for output."""
    return str(text)