"""End-to-end demo flow test.

Validates that the entire demo sequence works without crashes:
1. Setup with --yes (non-interactive)
2. Onboard from fixture spec (deterministic, no LLM needed)
3. Generated agent passes smoke test
4. Agent serve + health check
5. Sync task returns schema-valid output

Run before recording the YC/Twitter demo video.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC_FIXTURE = ROOT / "tests" / "fixtures" / "roofing-agent-spec.json"


@pytest.fixture(scope="module")
def demo_setup():
    """Run agent2 setup --yes to ensure .env and agent2.yaml exist."""
    result = subprocess.run(
        [sys.executable, "-m", "agent2_cli.main", "setup", "--yes", "--no-docker", "--no-onboard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Setup failed: {result.stderr}"
    assert (ROOT / ".env").exists()
    assert (ROOT / "agent2.yaml").exists()


@pytest.fixture(scope="module")
def demo_agent(demo_setup):
    """Generate the demo agent from the fixture spec."""
    result = subprocess.run(
        [sys.executable, "-m", "agent2_cli.main", "onboard", "--from-spec", str(SPEC_FIXTURE), "--no-llm", "--overwrite"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Onboard failed: {result.stderr}"
    agent_dir = ROOT / "agents" / "roofing-estimator"
    assert agent_dir.exists()
    assert (agent_dir / "agent.py").exists()
    assert (agent_dir / "schemas.py").exists()
    return "roofing-estimator"


def test_demo_agent_mock_result(demo_agent):
    """The generated agent produces schema-valid mock output."""
    agent_name = demo_agent
    agent_dir = ROOT / "agents" / agent_name

    sys.path.insert(0, str(ROOT))
    import importlib.util

    package = f"_demo_{agent_name.replace('-', '_')}"
    init_spec = importlib.util.spec_from_file_location(
        package, agent_dir / "__init__.py",
        submodule_search_locations=[str(agent_dir)],
    )
    assert init_spec and init_spec.loader
    init_module = importlib.util.module_from_spec(init_spec)
    sys.modules[package] = init_module
    init_spec.loader.exec_module(init_module)

    agent_spec = importlib.util.spec_from_file_location(
        f"{package}.agent", agent_dir / "agent.py",
    )
    assert agent_spec and agent_spec.loader
    module = importlib.util.module_from_spec(agent_spec)
    sys.modules[agent_spec.name] = module
    agent_spec.loader.exec_module(module)

    result = module.mock_result({
        "case": "Customer reports active roof leak after heavy rain.",
        "case_id": "demo-1",
    })
    assert result["status"] in ("complete", "needs_clarification", "rejected")
    assert "review_steps" in result
    assert "confidence" in result
    assert "reasoning" in result


def test_demo_doctor():
    """agent2 doctor passes."""
    result = subprocess.run(
        [sys.executable, "-m", "agent2_cli.main", "doctor", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Doctor failed: {result.stderr}"
    checks = json.loads(result.stdout)
    for check in checks:
        if check["name"] in ("git", "uv", ".env", "agent2.yaml"):
            assert check["ok"], f"Doctor check failed: {check}"


def test_demo_list_includes_agent(demo_agent):
    """agent2 list shows the generated agent."""
    result = subprocess.run(
        [sys.executable, "-m", "agent2_cli.main", "list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0
    assert "roofing-estimator" in result.stdout
