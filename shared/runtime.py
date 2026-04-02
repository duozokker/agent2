"""
Agent creation -- the core of the framework.

:func:`create_agent` builds a fully-configured :class:`pydantic_ai.Agent`
with:

* Model resolution  (parameter > config.yaml > env ``DEFAULT_MODEL``)
* System prompt resolution  (parameter > Langfuse prompt > fallback)
* OpenTelemetry / Langfuse instrumentation (when keys are present)

MCP toolsets can be passed via the ``toolsets`` parameter.  Additional
tools and integrations can be attached by calling ``agent.tool(...)``
after creation.
"""

from __future__ import annotations

import base64
import logging
import os
import threading
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent

from shared.config import Settings, load_agent_config

logger = logging.getLogger(__name__)

# Track whether we have already called instrument_all() in this process.
_instrumentation_done: bool = False
_instrumentation_lock = threading.Lock()
_langfuse_client: Any = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Provider prefixes that use "provider/org/model" convention in config but
# PydanticAI expects "provider:org/model".
_PROVIDER_PREFIXES = ("openrouter", "openai", "anthropic", "google-gla", "groq", "mistral")


def _normalize_model_id(model_id: str) -> str:
    """Convert ``provider/org/model`` to ``provider:org/model``.

    PydanticAI uses a colon to separate the provider from the model name,
    but the project config files use a slash for readability.  This function
    bridges the two conventions.

    Examples::

        openrouter/anthropic/claude-sonnet-4  ->  openrouter:anthropic/claude-sonnet-4
        openai:gpt-4o                         ->  openai:gpt-4o  (already correct)
        test                                  ->  test           (no change)
    """
    if ":" in model_id:
        # Already in PydanticAI format
        return model_id

    for prefix in _PROVIDER_PREFIXES:
        slash_prefix = prefix + "/"
        if model_id.startswith(slash_prefix):
            return prefix + ":" + model_id[len(slash_prefix):]

    return model_id


def _build_model(model_id: str, settings: Settings) -> Any:
    """Build a PydanticAI model object from a model ID string.

    Uses the official documented approach for each provider:
    - ``openrouter/...`` → ``OpenAIChatModel`` + ``OpenRouterProvider``
    - ``test`` → string ``"test"`` (PydanticAI test model)
    - Everything else → pass as string (PydanticAI resolves natively)
    """
    if model_id == "test":
        return "test"

    normalized = _normalize_model_id(model_id)

    # OpenRouter: use the official documented approach
    if normalized.startswith("openrouter:"):
        try:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openrouter import OpenRouterProvider

            or_model_name = normalized.split(":", 1)[1]  # e.g. "google/gemini-3-flash-preview"
            return OpenAIChatModel(
                or_model_name,
                provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
            )
        except ImportError:
            logger.warning("OpenRouterProvider not available; falling back to string model ID")
            return normalized

    # All other providers: use the string shorthand (groq:, mistral:, openai:, etc.)
    return normalized


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_agent(
    name: str,
    output_type: type[BaseModel],
    model: str | None = None,
    instructions: str | None = None,
    system_prompt: str | None = None,
    prompt_name: str | None = None,
    toolsets: list[Any] | None = None,
) -> Agent[None, Any]:
    """Create a PydanticAI agent with full framework integration.

    Parameters
    ----------
    name:
        Agent name, used to load ``agents/<name>/config.yaml`` and to
        identify the agent in logs / traces.
    output_type:
        A Pydantic model class that describes the structured output.
    model:
        LLM model identifier.  Falls back to ``config.yaml``'s ``model``
        field, then to the ``DEFAULT_MODEL`` env var.
    instructions:
        Explicit instructions string. When omitted the framework will try
        Langfuse (using *prompt_name*) and finally fall back to a generic
        prompt.
    system_prompt:
        Backwards-compatible alias for ``instructions``.
    prompt_name:
        Langfuse prompt name.  Defaults to ``<name>-system-prompt``.
    toolsets:
        Optional list of toolsets (e.g. ``MCPServerStreamableHTTP``
        instances) to attach to the agent.  These provide external
        tools that the LLM can call during a run.

    Returns
    -------
    pydantic_ai.Agent
        A ready-to-use agent.  Callers may attach additional tools via
        ``agent.tool(...)`` before running.
    """
    settings = Settings.from_env()
    config = load_agent_config(name)

    # -- Model resolution ----------------------------------------------------
    resolved_model = model or config.model or settings.default_model

    # When no LLM API key is configured, fall back to the PydanticAI "test"
    # model so that the agent object can be created without an error.  The
    # API layer detects the missing key separately and returns mock results.
    if not settings.has_llm_key:
        logger.info(
            "Agent '%s' has no OPENROUTER_API_KEY; using 'test' model (mock mode). "
            "Configured model was: %s",
            name,
            resolved_model,
        )
        resolved_model = "test"
    else:
        # Normalize model ID: convert "openrouter/provider/model" to
        # "openrouter:provider/model" which PydanticAI expects.
        resolved_model = _normalize_model_id(resolved_model)
        logger.info("Agent '%s' using model: %s", name, resolved_model)

    # -- System prompt resolution --------------------------------------------
    if instructions is not None and system_prompt is not None:
        raise TypeError("create_agent() accepts either instructions= or system_prompt=, not both")

    resolved_prompt: str | None = instructions if instructions is not None else system_prompt

    if resolved_prompt is None and prompt_name is not None:
        resolved_prompt = get_prompt(prompt_name, settings)

    if resolved_prompt is None and prompt_name is None:
        # Try the conventional name
        resolved_prompt = get_prompt(f"{name}-system-prompt", settings)

    if resolved_prompt is None:
        resolved_prompt = (
            f"You are {config.description or name}, a helpful AI assistant. "
            "Answer the user's question accurately and concisely."
        )

    # -- Instrumentation -----------------------------------------------------
    _setup_instrumentation(settings)

    # -- Build the model object ------------------------------------------------
    model_obj = _build_model(resolved_model, settings)

    provider_policy = dict(config.provider_policy)
    if config.provider_order and "order" not in provider_policy:
        provider_policy["order"] = config.provider_order
    allow_fallbacks = bool(provider_policy.get("allow_fallbacks", True))

    model_settings: dict[str, Any] | None = None
    provider_order = provider_policy.get("order", [])
    if provider_order and resolved_model != "test":
        try:
            from pydantic_ai.models.openrouter import OpenRouterModelSettings

            model_settings = OpenRouterModelSettings(
                openrouter_provider={
                    "order": provider_order,
                    "allow_fallbacks": allow_fallbacks,
                }
            )
            logger.info(
                "Agent '%s' pinned to provider(s): %s (allow_fallbacks=%s)",
                name,
                provider_order,
                allow_fallbacks,
            )
        except ImportError:
            logger.debug("OpenRouterModelSettings not available; skipping provider pinning")

    # -- Build the agent -----------------------------------------------------
    agent: Agent[None, Any] = Agent(
        model_obj,
        output_type=output_type,
        instructions=resolved_prompt,
        retries=config.max_retries,
        name=name,
        toolsets=toolsets or [],
        model_settings=model_settings,
    )

    logger.info("Agent '%s' created successfully", name)
    return agent


# ---------------------------------------------------------------------------
# Langfuse prompt management
# ---------------------------------------------------------------------------

def _get_langfuse_client(settings: Settings) -> Any:
    """Return a cached Langfuse client singleton (or None if not configured)."""
    global _langfuse_client

    if _langfuse_client is not None:
        return _langfuse_client
    if not settings.has_langfuse:
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        return _langfuse_client
    except Exception as exc:
        logger.debug("Could not create Langfuse client: %s", exc)
        return None


def get_prompt(prompt_name: str, settings: Settings, **variables: str) -> str | None:
    """Try to fetch a prompt from Langfuse.

    Returns ``None`` when Langfuse is not configured or the prompt does not
    exist.  All exceptions are swallowed so that agent creation never fails
    due to a Langfuse outage.
    """
    lf = _get_langfuse_client(settings)
    if lf is None:
        return None

    try:
        prompt = lf.get_prompt(prompt_name, label="production")
        compiled = prompt.compile(**variables)
        logger.info("Loaded prompt '%s' (v%s) from Langfuse", prompt_name, getattr(prompt, "version", "unknown"))
        return compiled
    except Exception as exc:
        logger.debug("Could not fetch prompt '%s' from Langfuse: %s", prompt_name, exc)
        return None


# ---------------------------------------------------------------------------
# OpenTelemetry / Langfuse instrumentation
# ---------------------------------------------------------------------------

def _setup_instrumentation(settings: Settings) -> None:
    """Configure OpenTelemetry to export traces to Langfuse.

    This is idempotent -- calling it multiple times is harmless.
    """
    global _instrumentation_done

    if _instrumentation_done:
        return

    with _instrumentation_lock:
        if _instrumentation_done:
            return

        if not settings.has_langfuse:
            logger.debug("Langfuse keys not set; skipping OTEL instrumentation")
            return

        try:
            auth_bytes = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
            auth_b64 = base64.b64encode(auth_bytes).decode()

            os.environ.setdefault(
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                f"{settings.langfuse_host}/api/public/otel",
            )
            os.environ.setdefault(
                "OTEL_EXPORTER_OTLP_HEADERS",
                f"Authorization=Basic {auth_b64}",
            )

            Agent.instrument_all()
            _instrumentation_done = True
            logger.info("PydanticAI OTEL instrumentation enabled (Langfuse)")
        except Exception as exc:
            logger.warning("Failed to set up OTEL instrumentation: %s", exc)
