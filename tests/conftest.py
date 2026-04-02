"""Shared test fixtures."""
import os
import pytest

# Set test environment variables before any imports
os.environ.setdefault("API_BEARER_TOKEN", "test-token")
os.environ.setdefault("OPENROUTER_API_KEY", "")
os.environ.setdefault("DEFAULT_MODEL", "test")
os.environ.setdefault("R2R_BASE_URL", "http://localhost:7272")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("LANGFUSE_HOST", "http://localhost:3000")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "")
os.environ.setdefault("KNOWLEDGE_MCP_URL", "http://localhost:9090/mcp")
os.environ.setdefault("TEMPORAL_HOST", "localhost:7233")
os.environ.setdefault("AGENT_NAME", "example-agent")

@pytest.fixture
def settings():
    from shared.config import Settings
    return Settings.from_env()

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}
