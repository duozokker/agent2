"""
Configuration management for Agent2.

Two levels of configuration:

1. **AgentConfig** -- per-agent settings loaded from ``agents/<name>/config.yaml``.
2. **Settings** -- global / environment-level settings populated from env vars.

Both are *frozen* dataclasses so they are safely shareable across async tasks.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
_TOKEN_SPLIT_RE = re.compile(r"[\s,;]+")


def _project_root() -> Path:
    """Return the project root directory.

    When running inside Docker the CWD is usually ``/app`` and the source tree
    is mounted there.  When running locally the project root is the parent of
    the ``shared/`` package directory.
    """
    return _PROJECT_ROOT


# ---------------------------------------------------------------------------
# Per-agent config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentConfig:
    """Per-agent configuration loaded from ``agents/<name>/config.yaml``."""

    name: str
    description: str = ""
    model: str = ""
    port: int = 8000
    timeout_seconds: int = 120
    max_retries: int = 3
    collections: list[str] = field(default_factory=list)
    provider_order: list[str] = field(default_factory=list)
    provider_policy: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)

    # Allow extra keys in the YAML without blowing up
    extra: dict[str, Any] = field(default_factory=dict, repr=False)


def load_agent_config(agent_name: str) -> AgentConfig:
    """Load configuration from ``agents/<name>/config.yaml``.

    Falls back to sensible defaults if the file does not exist so that
    development is friction-free.
    """
    config_path = _project_root() / "agents" / agent_name / "config.yaml"

    if not config_path.exists():
        return AgentConfig(name=agent_name)

    with open(config_path, "r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    # Pull out known fields; everything else goes into ``extra``.
    known_fields = {
        "name", "description", "model", "port",
        "timeout_seconds", "max_retries", "collections",
        "provider_order", "provider_policy", "capabilities",
    }
    known: dict[str, Any] = {}
    extra: dict[str, Any] = {}

    for key, value in raw.items():
        if key in known_fields:
            known[key] = value
        else:
            extra[key] = value

    # Ensure the name is always set
    known.setdefault("name", agent_name)

    # Normalise collections to a list
    if known.get("collections") is None:
        known["collections"] = []
    if known.get("provider_order") is None:
        known["provider_order"] = []
    if known.get("provider_policy") is None:
        known["provider_policy"] = {}
    if known.get("capabilities") is None:
        known["capabilities"] = []

    return AgentConfig(**known, extra=extra)


def load_collections_for_agent(agent_name: str) -> list[str]:
    """Read ``knowledge/collections.yaml`` and return collection names for *agent_name*.

    Supports two YAML layouts:

    **Dict-keyed** (used by the project)::

        collections:
          example-docs:
            agents: [example-agent]
            books_dir: books/example/

    **List-of-dicts** (also accepted)::

        collections:
          - name: example-docs
            agents: [example-agent]
            books_dir: books/example/

    Returns a flat list of collection names where the agent is listed.
    If the file is missing or malformed an empty list is returned.
    """
    collections_path = _project_root() / "knowledge" / "collections.yaml"

    if not collections_path.exists():
        return []

    try:
        with open(collections_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        return []

    raw = data.get("collections", {})
    result: list[str] = []

    if isinstance(raw, dict):
        # Dict-keyed format: {collection_name: {agents: [...], ...}}
        for col_name, col_data in raw.items():
            if not isinstance(col_data, dict):
                continue
            agents = col_data.get("agents", [])
            if agent_name in agents:
                result.append(col_name)
    elif isinstance(raw, list):
        # List-of-dicts format: [{name: ..., agents: [...], ...}]
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            agents = entry.get("agents", [])
            if agent_name in agents:
                name = entry.get("name")
                if name:
                    result.append(name)

    return result


def load_collection_catalog() -> dict[str, dict[str, Any]]:
    """Return the raw collection catalog from ``knowledge/collections.yaml``."""
    collections_path = _project_root() / "knowledge" / "collections.yaml"
    if not collections_path.exists():
        return {}

    with open(collections_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    raw = data.get("collections", {})
    return raw if isinstance(raw, dict) else {}


def _parse_bearer_tokens(raw: str | None) -> tuple[str, ...]:
    """Parse bearer tokens from a flexible env string."""
    if not raw:
        return ()

    return tuple(token for token in _TOKEN_SPLIT_RE.split(raw.strip()) if token)


# ---------------------------------------------------------------------------
# Global settings (from environment)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """Global settings populated from environment variables.

    Use :meth:`from_env` to create an instance.  All fields have sensible
    development defaults so the framework boots even when no ``.env`` file is
    present.
    """

    # -- LLM -----------------------------------------------------------------
    openrouter_api_key: str = ""
    default_model: str = "openrouter/anthropic/claude-sonnet-4"

    # -- R2R ------------------------------------------------------------------
    r2r_base_url: str = "http://localhost:7272"

    # -- Langfuse -------------------------------------------------------------
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # -- Temporal -------------------------------------------------------------
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "agent-tasks"

    # -- Knowledge MCP --------------------------------------------------------
    knowledge_mcp_url: str = "http://localhost:9090/mcp"

    # -- Auth -----------------------------------------------------------------
    api_bearer_tokens: tuple[str, ...] = ("dev-token-change-me",)

    # -- Redis ----------------------------------------------------------------
    redis_url: str = "redis://:myredissecret@localhost:6379"

    # -- Docling --------------------------------------------------------------
    docling_url: str = "http://localhost:5001"

    # -- Helpers --------------------------------------------------------------

    @classmethod
    def from_env(cls) -> Settings:
        """Build a ``Settings`` instance from the current environment."""

        tokens_raw = os.environ.get("API_BEARER_TOKENS")
        if tokens_raw is None:
            tokens_raw = os.environ.get("API_BEARER_TOKEN", "dev-token-change-me")
        tokens = _parse_bearer_tokens(tokens_raw) or ("dev-token-change-me",)

        return cls(
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            default_model=os.environ.get(
                "DEFAULT_MODEL", "openrouter/anthropic/claude-sonnet-4"
            ),
            r2r_base_url=os.environ.get("R2R_BASE_URL", "http://localhost:7272"),
            langfuse_host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
            langfuse_public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
            langfuse_secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
            temporal_host=os.environ.get("TEMPORAL_HOST", "localhost:7233"),
            temporal_namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
            temporal_task_queue=os.environ.get("TEMPORAL_TASK_QUEUE", "agent-tasks"),
            knowledge_mcp_url=os.environ.get(
                "KNOWLEDGE_MCP_URL", "http://localhost:9090/mcp"
            ),
            api_bearer_tokens=tokens,
            redis_url=os.environ.get("REDIS_URL", "redis://:myredissecret@localhost:6379"),
            docling_url=os.environ.get("DOCLING_URL", "http://localhost:5001"),
        )

    @property
    def has_llm_key(self) -> bool:
        """True when an OpenRouter API key is configured."""
        return bool(self.openrouter_api_key)

    @property
    def has_langfuse(self) -> bool:
        """True when both Langfuse keys are present."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)
