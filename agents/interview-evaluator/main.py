"""FastAPI application entry point for the interview evaluator agent."""

from __future__ import annotations

from shared.api import create_app

app = create_app("interview-evaluator")
