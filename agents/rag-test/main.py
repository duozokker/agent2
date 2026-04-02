"""FastAPI application for the RAG test agent."""
from shared.api import create_app
app = create_app("rag-test")
