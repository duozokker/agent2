"""Agent2 CLI entrypoint."""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from agent2_cli.doctor import run_doctor
from agent2_cli.generator import GenerationError
from agent2_cli.onboarding import run_onboarding, textual_available
from agent2_cli.setup import DEFAULT_MODEL, MODEL_CHOICES, SetupOptions, payload_as_json, run_setup
from shared.config import Settings, load_agent_config, load_framework_config

app = typer.Typer(help="Agent2 framework CLI")
console = Console()


def _root() -> Path:
    if os.environ.get("AGENT2_PROJECT_ROOT"):
        return Path(os.environ["AGENT2_PROJECT_ROOT"]).resolve()
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists() and (cwd / "shared").exists():
        return cwd
    return Path(__file__).resolve().parent.parent


_MODEL_LABELS = {
    "~anthropic/claude-sonnet-latest": "Claude Sonnet (recommended)",
    "~openai/gpt-latest": "GPT Latest",
    "~moonshotai/kimi-latest": "Kimi Latest",
    "~openai/gpt-mini-latest": "GPT Mini (fast, affordable)",
    "~anthropic/claude-opus-latest": "Claude Opus (highest quality)",
}


def _setup_wizard(
    openrouter_key: str | None, model: str, profile: str, no_docker: bool, no_onboard: bool,
) -> tuple[SetupOptions, bool]:
    """Run the step-by-step setup wizard using questionary prompts."""

    import questionary
    from questionary import Style

    style = Style([
        ("qmark", "fg:#FF3B30 bold"),
        ("question", "fg:#ffffff bold"),
        ("answer", "fg:#FF3B30 bold"),
        ("pointer", "fg:#FF3B30 bold"),
        ("highlighted", "fg:#FF3B30 bold"),
        ("selected", "fg:#FF3B30"),
        ("instruction", "fg:#9A9590"),
        ("text", "fg:#9A9590"),
        ("separator", "fg:#333333"),
    ])

    console.print()
    console.print("[bold #FF3B30]  ●[/bold #FF3B30]  [bold]Agent2 Setup[/bold]")
    console.print("[#9A9590]  Configure your agent framework in 30 seconds.[/]")
    console.print()

    console.print("[bold #FF3B30][1/4][/] [bold]OpenRouter API key[/]")
    console.print("[#777]  Get yours at openrouter.ai/keys[/]")
    key = openrouter_key or questionary.password(
        "  API key:", style=style,
    ).ask()
    if key is None:
        raise KeyboardInterrupt
    key = key.strip()
    if key:
        console.print(f"  [green]✓[/green] Key set ({key[:12]}...)")
    else:
        console.print("  [#777]· Skipped (mock mode)[/]")
    console.print()

    console.print("[bold #FF3B30][2/4][/] [bold]Default model[/]")
    model_choices = [
        questionary.Choice(title=_MODEL_LABELS.get(m, m), value=m)
        for m in MODEL_CHOICES
    ]
    model_choices.append(questionary.Choice(title="Custom model ID...", value="__custom__"))
    selected_model = questionary.select(
        "  Select model:", choices=model_choices, default=model, style=style,
    ).ask()
    if selected_model is None:
        raise KeyboardInterrupt
    if selected_model == "__custom__":
        selected_model = questionary.text("  Custom model ID:", style=style).ask()
        if not selected_model:
            selected_model = model
    console.print(f"  [green]✓[/green] {selected_model}")
    console.print()

    console.print("[bold #FF3B30][3/4][/] [bold]Stack profile[/]")
    selected_profile = questionary.select(
        "  Select profile:",
        choices=[
            questionary.Choice(title="core — fast local agent API (recommended)", value="core"),
            questionary.Choice(title="full — adds RAG, Knowledge MCP, Langfuse, Temporal", value="full"),
        ],
        default=profile,
        style=style,
    ).ask()
    if selected_profile is None:
        raise KeyboardInterrupt
    console.print(f"  [green]✓[/green] {selected_profile}")
    console.print()

    start_docker = False
    if not no_docker:
        console.print("[bold #FF3B30][4/4][/] [bold]Docker services[/]")
        start_docker = questionary.confirm(
            "  Start Docker services now?", default=True, style=style,
        ).ask()
        if start_docker is None:
            raise KeyboardInterrupt
        console.print(f"  [green]✓[/green] {'Starting' if start_docker else 'Skipped'}")
        console.print()
    else:
        console.print("[bold #FF3B30][4/4][/] [bold]Docker[/] [#777]skipped (--no-docker)[/]")
        console.print()

    launch_onboard = False
    if not no_onboard:
        launch_onboard = questionary.confirm(
            "  Clone your first expert brain now?",
            default=True,
            style=style,
        ).ask()
        if launch_onboard is None:
            raise KeyboardInterrupt

    options = SetupOptions(
        openrouter_api_key=key,
        default_model=selected_model,
        stack_profile=selected_profile,
        telemetry_enabled=selected_profile == "full",
        no_docker=no_docker or not start_docker,
        no_onboard=no_onboard,
        yes=False,
        dry_run=False,
        json_output=False,
    )
    return options, launch_onboard


@app.command()
def setup(
    openrouter_key: Annotated[Optional[str], typer.Option("--openrouter-key", help="OpenRouter API key")] = None,
    model: Annotated[str, typer.Option(help="Default model ID")] = DEFAULT_MODEL,
    profile: Annotated[str, typer.Option("--profile", help="core or full")] = "core",
    telemetry: Annotated[bool, typer.Option("--telemetry/--no-telemetry")] = False,
    no_docker: Annotated[bool, typer.Option("--no-docker", help="Do not run docker compose up")] = False,
    no_onboard: Annotated[bool, typer.Option("--no-onboard", help="Do not prompt for first Brain Clone")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Accept recommended defaults")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show planned changes without writing files")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable output")] = False,
    tui: Annotated[bool, typer.Option("--tui", help="Use legacy fullscreen Textual TUI")] = False,
) -> None:
    """Configure .env, agent2.yaml, and optionally start Docker."""

    launch_onboard = False
    if tui and not yes and not json_output and textual_available():
        try:
            from agent2_cli.setup_tui import run_setup_tui

            wizard = run_setup_tui(default_model=model, default_profile=profile)
            options = wizard.options
            launch_onboard = wizard.create_first_agent and not options.no_onboard
        except KeyboardInterrupt:
            raise typer.Exit(130) from None
    elif not yes and not json_output:
        try:
            options, launch_onboard = _setup_wizard(openrouter_key, model, profile, no_docker, no_onboard)
        except KeyboardInterrupt:
            raise typer.Exit(130) from None
    else:
        options = SetupOptions(
            openrouter_api_key=openrouter_key or "",
            default_model=model,
            stack_profile=profile,
            telemetry_enabled=telemetry or profile == "full",
            no_docker=no_docker,
            no_onboard=no_onboard,
            yes=yes,
            dry_run=dry_run,
            json_output=json_output,
        )

    result = run_setup(_root(), options)
    if json_output:
        console.print(payload_as_json(result))
        return

    if not dry_run:
        _inject_env_into_process(result.get("env", {}))

    has_key = bool(options.openrouter_api_key)
    if has_key and not dry_run:
        _validate_key(options.openrouter_api_key, options.default_model)

    console.print()
    verb = "Would write" if dry_run else "Wrote"
    console.print(f"  [green]✓[/green] {verb} [bold].env[/bold] and [bold]agent2.yaml[/bold]")
    console.print(
        f"  [green]✓[/green] Model: [#FF3B30]{options.default_model}[/]  "
        f"Profile: [#FF3B30]{options.stack_profile}[/]"
    )
    console.print()

    if launch_onboard and not dry_run:
        console.print("[bold]  Starting Brain Clone interview...[/bold]")
        console.print()
        run_onboarding(
            project_root=_root(), no_llm=False, overwrite=False,
            use_tui=False, agentic=has_key, console=console,
        )


@app.command()
def onboard(
    from_spec: Annotated[Optional[Path], typer.Option("--from-spec", help="Generate from an AgentSpec JSON file")] = None,
    no_llm: Annotated[bool, typer.Option("--no-llm", help="Use deterministic questionnaire/spec only")] = False,
    no_tui: Annotated[bool, typer.Option("--no-tui", help="Use Rich prompts instead of the Textual form")] = False,
    agentic: Annotated[bool, typer.Option("--agentic", help="Use LLM-powered adaptive interview instead of static form")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite an existing generated agent")] = False,
) -> None:
    """Run the Brain Clone onboarding harness."""

    use_tui = from_spec is None and not no_tui and textual_available()
    use_agentic = agentic or (from_spec is None and not no_llm and Settings.from_env().has_llm_key and not no_tui)
    try:
        run_onboarding(
            project_root=_root(),
            from_spec=from_spec,
            no_llm=no_llm,
            overwrite=overwrite,
            use_tui=use_tui,
            agentic=use_agentic,
            console=console,
        )
    except GenerationError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def doctor(json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable output")] = False) -> None:
    """Validate local Agent2 setup."""

    results = run_doctor(_root())
    if json_output:
        console.print(json.dumps([result.__dict__ for result in results], indent=2))
        raise typer.Exit(0 if all(result.ok for result in results) else 1)
    table = Table(title="Agent2 Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for result in results:
        table.add_row(result.name, "ok" if result.ok else "fail", result.detail)
    console.print(table)
    if not all(result.ok for result in results):
        raise typer.Exit(1)


@app.command("list")
def list_agents() -> None:
    """List local Agent2 agents."""

    table = Table(title="Agent2 Agents")
    table.add_column("Agent")
    table.add_column("Port")
    table.add_column("Model")
    table.add_column("Capabilities")
    for config_path in sorted((_root() / "agents").glob("*/config.yaml")):
        if config_path.parent.name.startswith("_"):
            continue
        config = load_agent_config(config_path.parent.name)
        table.add_row(config.name, str(config.port), config.model or "<global>", ", ".join(config.capabilities))
    console.print(table)


@app.command()
def run(
    agent: Annotated[str, typer.Argument(help="Agent name")],
    text: Annotated[str, typer.Option("--text", help="Input text")] = "hello from agent2 cli",
    token: Annotated[str, typer.Option("--token", help="Bearer token")] = "dev-token-change-me",
) -> None:
    """Send a sync test request to a local agent."""

    _ensure_agent_exists(agent)
    config = load_agent_config(agent)
    url = f"http://localhost:{config.port}/tasks?mode=sync"
    body = json.dumps({"input": {"text": text}}).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            console.print_json(response.read().decode())
    except urllib.error.URLError as exc:
        raise typer.BadParameter(f"Could not reach {url}: {exc}") from exc


@app.command()
def serve(
    agent: Annotated[str, typer.Argument(help="Agent name")],
    port: Annotated[Optional[int], typer.Option("--port", help="Override the configured port")] = None,
    host: Annotated[str, typer.Option("--host", help="Bind host")] = "0.0.0.0",
) -> None:
    """Serve an Agent2 agent locally without editing docker-compose.yml."""

    import uvicorn
    from shared.api import create_app

    _ensure_agent_exists(agent)
    config = load_agent_config(agent)
    uvicorn.run(create_app(agent), host=host, port=port or config.port)


@app.command("publish-check")
def publish_check() -> None:
    """Run release safety checks for generated agents."""

    secret_pattern = re.compile(r"(gho_|sk-[A-Za-z0-9_-]{12,}|BEGIN (RSA|OPENSSH|PRIVATE)|/Users/)")
    failures: list[str] = []
    for path in list((_root() / "agents").glob("*/**/*")) + list((_root() / "docs").glob("**/*")):
        if path.is_file() and path.suffix in {".py", ".yaml", ".yml", ".md", ".json"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if secret_pattern.search(text):
                failures.append(str(path.relative_to(_root())))
    try:
        subprocess.run(["docker", "compose", "config", "--quiet"], cwd=_root(), check=True)
    except Exception as exc:
        failures.append(f"docker compose config failed: {exc}")
    if failures:
        for failure in failures:
            console.print(f"[red]fail[/red] {failure}")
        raise typer.Exit(1)
    config = load_framework_config(_root() / "agent2.yaml")
    console.print(f"[bold green]publish-check passed[/bold green] default_model={config.default_model or '<env>'}")


def _inject_env_into_process(env_values: dict[str, str]) -> None:
    """Push setup-generated env values into the running process so that
    subsequent calls (like ``agent2 onboard``) pick them up immediately
    without the user having to ``source .env`` manually."""

    for key, value in env_values.items():
        if value:
            os.environ[key] = value


def _validate_key(api_key: str, model_id: str) -> None:
    """Quick LLM connectivity check after setup."""

    key_preview = api_key[:12] + "..." if len(api_key) > 12 else api_key
    console.print(f"  [#777]Validating key ({key_preview}) against {model_id}...[/]", end=" ")
    try:
        import asyncio
        from pydantic_ai import Agent
        from shared.runtime import _build_model

        settings = Settings.from_env()
        model = _build_model(model_id or settings.default_model, settings)
        agent: Agent[None, str] = Agent(model, output_type=str, instructions="Reply: ok")
        asyncio.run(agent.run("test"))
        console.print("[green]✓ valid[/green]")
    except Exception as exc:
        msg = str(exc)
        if "401" in msg or "auth" in msg.lower():
            console.print("[#FF3B30]✗ invalid[/]")
            console.print("  [#777]Check your key at openrouter.ai/keys[/]")
        else:
            console.print(f"[yellow]⚠ {msg[:80]}[/yellow]")


def _ensure_agent_exists(agent: str) -> None:
    config_path = _root() / "agents" / agent / "config.yaml"
    if not config_path.exists():
        raise typer.BadParameter(f"Unknown agent '{agent}'. Expected {config_path}.")


if __name__ == "__main__":
    app()
