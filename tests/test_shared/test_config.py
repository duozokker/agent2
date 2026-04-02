"""Tests for shared.config module."""

from shared.config import Settings, load_agent_config, load_collections_for_agent

def test_settings_from_env():
    """Settings loads from environment variables."""
    s = Settings.from_env()
    assert s.api_bearer_tokens == ("test-token",)
    assert s.default_model == "test"

def test_settings_has_llm_key_false(monkeypatch):
    """has_llm_key is False when key is empty."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    s = Settings.from_env()
    assert s.has_llm_key is False

def test_settings_has_llm_key_true(monkeypatch):
    """has_llm_key is True when key is set."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-123")
    s = Settings.from_env()
    assert s.has_llm_key is True

def test_settings_multiple_tokens(monkeypatch):
    """Multiple bearer tokens parsed from CSV."""
    monkeypatch.setenv("API_BEARER_TOKENS", "token-a; token-b token-c")
    s = Settings.from_env()
    assert len(s.api_bearer_tokens) == 3
    assert "token-b" in s.api_bearer_tokens


def test_load_agent_config_reads_provider_policy():
    config = load_agent_config("provider-policy-demo")
    assert config.provider_order == ["anthropic"]
    assert config.provider_policy["allow_fallbacks"] is True
    assert "provider_policy" not in config.extra

def test_load_collections_for_agent():
    """Collections resolved from collections.yaml."""
    # This should work if knowledge/collections.yaml exists
    collections = load_collections_for_agent("example-agent")
    assert isinstance(collections, list)
