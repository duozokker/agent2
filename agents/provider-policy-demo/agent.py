"""Framework demo for provider policy wiring."""

from __future__ import annotations

from shared.config import load_agent_config
from shared.runtime import create_agent

from .schemas import ProviderPolicyDemoResult

output_type = ProviderPolicyDemoResult
_config = load_agent_config("provider-policy-demo")

agent = create_agent(
    name="provider-policy-demo",
    output_type=ProviderPolicyDemoResult,
    instructions="You are a provider policy demo agent.",
)


def mock_result(_input_data: dict) -> dict:
    policy = dict(_config.provider_policy)
    return {
        "status": "configured",
        "provider_order": list(policy.get("order", _config.provider_order)),
        "allow_fallbacks": bool(policy.get("allow_fallbacks", True)),
        "confidence": 0.99,
    }
