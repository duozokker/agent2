"""Domain-specific tools for the example agent."""

def count_words(text: str) -> int:
    """Count words in the given text."""
    return len(text.split())

def detect_language(text: str) -> str:
    """Simple language detection based on common words."""
    de_words = {"der", "die", "das", "und", "ist", "ein", "eine", "für", "mit", "auf"}
    en_words = {"the", "is", "and", "of", "to", "in", "a", "for", "with", "on"}
    words = set(text.lower().split()[:100])
    de_score = len(words & de_words)
    en_score = len(words & en_words)
    if de_score > en_score:
        return "de"
    return "en"
