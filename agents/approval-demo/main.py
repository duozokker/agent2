"""FastAPI application for the approval demo agent."""

from shared.api import create_app

app = create_app("approval-demo")
