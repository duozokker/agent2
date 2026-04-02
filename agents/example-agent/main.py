"""FastAPI application for the example agent."""
from shared.api import create_app

app = create_app("example-agent")
