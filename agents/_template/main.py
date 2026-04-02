"""FastAPI application entry point for the template agent."""

from __future__ import annotations

from shared.api import create_app

app = create_app("my-agent")
