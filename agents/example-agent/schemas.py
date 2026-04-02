"""Output schemas for the example agent."""
from pydantic import BaseModel, Field

class DocumentSummary(BaseModel):
    """Structured summary of a document."""
    title: str = Field(description="A concise title for the document")
    summary: str = Field(description="2-3 sentence summary of the main content")
    key_points: list[str] = Field(description="3-5 key takeaways from the document")
    word_count: int = Field(description="Approximate word count of the input document", ge=0)
    language: str = Field(description="Detected language of the document (e.g., 'en', 'de')")
    confidence: float = Field(description="Confidence in the analysis (0.0-1.0)", ge=0.0, le=1.0)
