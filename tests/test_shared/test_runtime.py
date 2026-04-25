"""Tests for shared.runtime."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from shared.config import AgentConfig
from shared.runtime import create_agent


class DemoOutput(BaseModel):
    ok: bool


def test_create_agent_uses_provider_policy_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    agent = create_agent(
        "provider-policy-demo",
        DemoOutput,
        instructions="You are testing provider pinning.",
    )

    provider_settings = agent.model_settings["openrouter_provider"]
    assert provider_settings["order"] == ["anthropic"]
    assert provider_settings["allow_fallbacks"] is True


def test_create_agent_defaults_provider_order_to_no_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setattr(
        "shared.runtime.load_agent_config",
        lambda _name: AgentConfig(
            name="sticky-agent",
            model="openrouter/anthropic/claude-sonnet-4",
            provider_order=["anthropic"],
        ),
    )

    agent = create_agent(
        "sticky-agent",
        DemoOutput,
        instructions="You are testing sticky provider defaults.",
    )

    provider_settings = agent.model_settings["openrouter_provider"]
    assert provider_settings["order"] == ["anthropic"]
    assert provider_settings["allow_fallbacks"] is False


def test_create_agent_rejects_provider_policy_for_non_openrouter_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setattr(
        "shared.runtime.load_agent_config",
        lambda _name: AgentConfig(
            name="bad-provider-agent",
            model="openai/gpt-4o",
            provider_order=["openai"],
        ),
    )

    with pytest.raises(RuntimeError, match="not an OpenRouter model"):
        create_agent(
            "bad-provider-agent",
            DemoOutput,
            instructions="You are testing invalid provider policy placement.",
        )


def test_create_agent_rejects_non_boolean_provider_fallback_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setattr(
        "shared.runtime.load_agent_config",
        lambda _name: AgentConfig(
            name="bad-fallback-agent",
            model="openrouter/anthropic/claude-sonnet-4",
            provider_order=["anthropic"],
            provider_policy={"allow_fallbacks": "false"},
        ),
    )

    with pytest.raises(RuntimeError, match="allow_fallbacks must be a boolean"):
        create_agent(
            "bad-fallback-agent",
            DemoOutput,
            instructions="You are testing invalid fallback policy.",
        )


def test_create_agent_rejects_conflicting_provider_order_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setattr(
        "shared.runtime.load_agent_config",
        lambda _name: AgentConfig(
            name="conflicting-provider-agent",
            model="openrouter/anthropic/claude-sonnet-4",
            provider_order=["anthropic"],
            provider_policy={"order": ["openai"]},
        ),
    )

    with pytest.raises(RuntimeError, match="conflicting provider_order"):
        create_agent(
            "conflicting-provider-agent",
            DemoOutput,
            instructions="You are testing conflicting provider settings.",
        )


def test_create_agent_rejects_duplicate_instruction_parameters() -> None:
    with pytest.raises(TypeError):
        create_agent(
            "example-agent",
            DemoOutput,
            instructions="Use instructions.",
            system_prompt="Use system prompt.",
        )


def test_create_agent_supports_system_prompt_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    agent = create_agent(
        "example-agent",
        DemoOutput,
        system_prompt="Alias prompt works.",
    )

    assert list(agent._instructions) == ["Alias prompt works."]
