"""FastAPI application for the resume demo agent."""

from shared.api import create_app

app = create_app("resume-demo")
