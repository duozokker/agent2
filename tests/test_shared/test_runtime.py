"""Tests for shared.runtime."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

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
