"""LLM integration boundary.

The application currently uses the local classifier and extractive summarizer,
so it works without transmitting private email contents to a third party.
"""

def is_configured() -> bool:
    return False
