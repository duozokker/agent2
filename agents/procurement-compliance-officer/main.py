"""FastAPI entry point for the procurement compliance officer agent."""

from __future__ import annotations

from shared.api import create_app

app = create_app("procurement-compliance-officer")
