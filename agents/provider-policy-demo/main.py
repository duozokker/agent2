"""FastAPI application for the provider policy demo agent."""

from shared.api import create_app

app = create_app("provider-policy-demo")
