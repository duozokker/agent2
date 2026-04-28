"""Tests for Agent2 Brain Clone spec generation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from agent2_cli.generator import generate_agent_from_spec
from agent2_cli.onboarding import load_spec


def test_agent_spec_fixture_validates() -> None:
    spec = load_spec(Path("tests/fixtures/roofing-agent-spec.json"))
    assert spec.name == "roofing-estimator"
    assert {outcome.name for outcome in spec.outcomes} >= {"complete", "needs_clarification", "rejected"}


def test_generator_creates_importable_agent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    spec = load_spec(Path("tests/fixtures/roofing-agent-spec.json"))
    generated = generate_agent_from_spec(spec, project_root=tmp_path)

    assert (generated / "agent.py").exists()
    assert (generated / "schemas.py").exists()
    assert (generated / "config.yaml").exists()
    assert (tmp_path / "knowledge" / "books" / "roofing-estimator-books" / "README.md").exists()
    assert (tmp_path / "tests" / "promptfoo" / spec.name / "eval.yaml").exists()

    package = "_tmp_roofing_estimator"
    init_spec = importlib.util.spec_from_file_location(
        package,
        generated / "__init__.py",
        submodule_search_locations=[str(generated)],
    )
    assert init_spec and init_spec.loader
    init_module = importlib.util.module_from_spec(init_spec)
    sys.modules[package] = init_module
    init_spec.loader.exec_module(init_module)

    agent_spec = importlib.util.spec_from_file_location(f"{package}.agent", generated / "agent.py")
    assert agent_spec and agent_spec.loader
    module = importlib.util.module_from_spec(agent_spec)
    sys.modules[agent_spec.name] = module
    agent_spec.loader.exec_module(module)

    result = module.mock_result({"case": "Leak over kitchen skylight."})
    parsed = module.RoofingEstimatorResult.model_validate(result)
    assert parsed.status == "complete"
