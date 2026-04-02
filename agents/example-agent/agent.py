"""
Example Agent — demonstrates the Agent2 framework.

This agent takes a document text as input and returns a structured summary.
It showcases: output_type enforcement, custom tools, and framework integration.
"""
from shared.runtime import create_agent
from .schemas import DocumentSummary
from . import tools

# Create the agent with structured output
agent = create_agent(
    name="example-agent",
    output_type=DocumentSummary,
    system_prompt=(
        "You are a document analysis assistant. Given a document text, "
        "produce a structured summary. Use the count_words tool to get "
        "an accurate word count. Use detect_language to identify the language. "
        "Be concise and accurate in your analysis."
    ),
)

# Register domain-specific tools
@agent.tool_plain
def count_words(text: str) -> int:
    """Count the number of words in the given text."""
    return tools.count_words(text)

@agent.tool_plain
def detect_language(text: str) -> str:
    """Detect the language of the text. Returns ISO 639-1 code (e.g., 'en', 'de')."""
    return tools.detect_language(text)
