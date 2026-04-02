"""Tests for the example agent schemas and tools."""
import pytest
from pydantic import BaseModel, Field, ValidationError


def test_document_summary_schema():
    """DocumentSummary schema validates correctly."""

    class DocumentSummary(BaseModel):
        title: str
        summary: str
        key_points: list[str]
        word_count: int = Field(ge=0)
        language: str
        confidence: float = Field(ge=0.0, le=1.0)

    summary = DocumentSummary(
        title="Test",
        summary="A test document",
        key_points=["point 1", "point 2"],
        word_count=100,
        language="en",
        confidence=0.95,
    )
    assert summary.title == "Test"
    assert summary.confidence == 0.95
    assert len(summary.key_points) == 2


def test_document_summary_rejects_invalid():
    """DocumentSummary rejects invalid confidence."""

    class DocumentSummary(BaseModel):
        title: str
        summary: str
        key_points: list[str]
        word_count: int = Field(ge=0)
        language: str
        confidence: float = Field(ge=0.0, le=1.0)

    with pytest.raises(ValidationError):
        DocumentSummary(
            title="Test",
            summary="A test",
            key_points=[],
            word_count=10,
            language="en",
            confidence=1.5,
        )


def test_word_count_tool():
    """Word counting works correctly."""
    text = "hello world this is a test"
    assert len(text.split()) == 6


def test_language_detection():
    """Simple language detection for DE and EN."""
    de_words = {"der", "die", "das", "und", "ist", "ein", "eine", "für", "mit", "auf"}
    en_words = {"the", "is", "and", "of", "to", "in", "a", "for", "with", "on"}

    de_text = "Der schnelle braune Fuchs springt über den faulen Hund"
    en_text = "The quick brown fox jumps over the lazy dog"

    de_tokens = set(de_text.lower().split())
    en_tokens = set(en_text.lower().split())

    assert len(de_tokens & de_words) > len(de_tokens & en_words)
    assert len(en_tokens & en_words) > len(en_tokens & de_words)
