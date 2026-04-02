"""Output schema for the RAG test agent."""
from pydantic import BaseModel, Field

class KnowledgeAnswer(BaseModel):
    answer: str = Field(description="The answer to the question based on the knowledge base")
    sources_used: list[str] = Field(description="Which sources/documents were referenced")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the answer")
    knowledge_found: bool = Field(description="Whether relevant knowledge was found in the search")
