"""Tests for the Agent2 CLI setup and doctor helpers."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agent2_cli.main import app
from agent2_cli.setup import SetupOptions, run_setup
from shared.config import load_framework_config


def test_setup_dry_run_json() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["setup", "--dry-run", "--json", "--yes", "--no-docker"])
    assert result.exit_code == 0
    assert '"dry_run": true' in result.output
    assert "OPENROUTER_API_KEY" in result.output


def test_setup_writes_env_and_agent2_yaml_with_backup(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    config_path = tmp_path / "agent2.yaml"
    env_path.write_text("OLD=1\n", encoding="utf-8")
    config_path.write_text("default_model: old\n", encoding="utf-8")

    result = run_setup(
        tmp_path,
        SetupOptions(
            openrouter_api_key="sk-test",
            default_model="~anthropic/claude-sonnet-latest",
            no_docker=True,
        ),
    )

    assert result["changed"] is True
    assert "OPENROUTER_API_KEY=sk-test" in env_path.read_text(encoding="utf-8")
    assert list(tmp_path.glob(".env.bak-*"))
    assert list(tmp_path.glob("agent2.yaml.bak-*"))
    config = load_framework_config(config_path)
    assert config.default_model == "~anthropic/claude-sonnet-latest"


def test_onboard_from_spec_no_llm(tmp_path: Path, monkeypatch) -> None:
    spec_path = Path("tests/fixtures/roofing-agent-spec.json").resolve()
    monkeypatch.setenv("AGENT2_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "agents").mkdir()
    (tmp_path / "tests").mkdir()

    runner = CliRunner()
    result = runner.invoke(app, ["onboard", "--from-spec", str(spec_path), "--no-llm"])

    assert result.exit_code == 0
    assert (tmp_path / "agents" / "roofing-estimator" / "agent.py").exists()
