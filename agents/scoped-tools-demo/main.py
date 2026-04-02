"""FastAPI application for the scoped tools demo agent."""

from shared.api import create_app

app = create_app("scoped-tools-demo")
