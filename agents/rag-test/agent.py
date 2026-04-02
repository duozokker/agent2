"""
RAG Test Agent — answers questions using the Knowledge MCP server.

Demonstrates the full pipeline:
1. Receives a question
2. Searches the knowledge base via MCP
3. Returns a structured answer with sources
"""
import os

from pydantic_ai.mcp import MCPServerStreamableHTTP

from shared.runtime import create_agent
from .schemas import KnowledgeAnswer

# Connect to Knowledge MCP server for RAG search
knowledge_mcp_url = os.environ.get("KNOWLEDGE_MCP_URL", "http://localhost:9090/mcp")
knowledge_server = MCPServerStreamableHTTP(knowledge_mcp_url)

agent = create_agent(
    name="rag-test",
    output_type=KnowledgeAnswer,
    system_prompt=(
        "You are a knowledge assistant. When asked a question:\n"
        "1. ALWAYS use the search tool to find relevant information first\n"
        "2. Base your answer on the search results\n"
        "3. If no relevant results found, set knowledge_found=false\n"
        "4. List which sources you used in sources_used\n"
        "5. Set confidence based on how well the search results answer the question"
    ),
    toolsets=[knowledge_server],
)
