"""
TODO: Define your agent's output schema here.

The output schema defines the structured data your agent MUST produce.
PydanticAI will enforce this schema — the agent retries until output validates.
"""
from pydantic import BaseModel, Field

class MyAgentResult(BaseModel):
    """TODO: Replace with your domain-specific output schema."""
    status: str = Field(description="Result status")
    data: dict = Field(default_factory=dict, description="Result data")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
