"""Fullscreen Textual setup wizard for Agent2."""

from __future__ import annotations

from dataclasses import dataclass

from agent2_cli.setup import DEFAULT_MODEL, MODEL_CHOICES, SetupOptions


@dataclass(frozen=True)
class SetupWizardResult:
    """Result returned by the interactive setup wizard."""

    options: SetupOptions
    create_first_agent: bool


def run_setup_tui(*, default_model: str = DEFAULT_MODEL, default_profile: str = "core") -> SetupWizardResult:
    """Run the fullscreen setup wizard."""

    from textual import on
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, Switch

    class SetupApp(App[SetupWizardResult]):
        CSS = """
        Screen {
            background: #0d0f12;
            color: #f4f4f5;
        }

        #shell {
            height: 100%;
        }

        #hero {
            height: 7;
            padding: 1 3;
            background: #15171b;
            border-bottom: tall #2b3038;
        }

        #brand {
            color: #ffffff;
            text-style: bold;
        }

        #subtitle {
            color: #a1a1aa;
        }

        #body {
            height: 1fr;
        }

        #rail {
            width: 33;
            padding: 2;
            background: #111317;
            border-right: tall #272b33;
        }

        .rail-title {
            color: #ffffff;
            text-style: bold;
            margin-bottom: 1;
        }

        .rail-muted {
            color: #71717a;
        }

        #panel {
            width: 1fr;
            padding: 2 3;
        }

        #card {
            height: 1fr;
            border: tall #272b33;
            background: #12151a;
            padding: 1 2;
        }

        .section {
            color: #ff5a4f;
            text-style: bold;
            margin: 1 0;
        }

        Label {
            margin-top: 1;
            color: #d4d4d8;
        }

        Input, Select {
            margin-bottom: 1;
        }

        .switch-row {
            height: 3;
            margin-top: 1;
        }

        .switch-label {
            width: 36;
            color: #d4d4d8;
        }

        #actions {
            height: 4;
            padding-top: 1;
        }

        Button {
            margin-right: 1;
            min-width: 18;
        }

        #summary {
            color: #d4d4d8;
            background: #0d0f12;
            border: tall #2b3038;
            padding: 1 2;
            margin-top: 1;
        }
        """

        BINDINGS = [("escape", "quit", "Quit")]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical(id="shell"):
                with Container(id="hero"):
                    yield Static("Agent2 Setup", id="brand")
                    yield Static("Configure provider, model, stack profile, telemetry, and first-agent flow.", id="subtitle")
                with Horizontal(id="body"):
                    with Vertical(id="rail"):
                        yield Static("Day 0 checklist", classes="rail-title")
                        yield Static("1. OpenRouter credentials", classes="rail-muted")
                        yield Static("2. Model and provider policy", classes="rail-muted")
                        yield Static("3. Docker and observability profile", classes="rail-muted")
                        yield Static("4. Optional Brain Clone launch", classes="rail-muted")
                    with Vertical(id="panel"):
                        with Container(id="card"):
                            yield Static("Provider", classes="section")
                            yield Label("OpenRouter API key")
                            yield Input(value="", password=True, placeholder="sk-or-...", id="openrouter_key")
                            yield Label("Default model")
                            yield Select(
                                [(choice, choice) for choice in MODEL_CHOICES],
                                value=default_model,
                                id="model",
                            )
                            yield Label("Custom model override")
                            yield Input(
                                value="",
                                placeholder="Leave empty to use the selected model",
                                id="custom_model",
                            )
                            yield Static("Stack", classes="section")
                            yield Label("Profile")
                            yield Select(
                                [("core - fast local agent API", "core"), ("full - RAG, Knowledge MCP, Langfuse", "full")],
                                value=default_profile,
                                id="profile",
                            )
                            with Horizontal(classes="switch-row"):
                                yield Static("Enable telemetry / Langfuse", classes="switch-label")
                                yield Switch(value=False, id="telemetry")
                            with Horizontal(classes="switch-row"):
                                yield Static("Start Docker services now", classes="switch-label")
                                yield Switch(value=True, id="docker")
                            with Horizontal(classes="switch-row"):
                                yield Static("Create first Brain Clone agent next", classes="switch-label")
                                yield Switch(value=True, id="create_agent")
                            yield Static("", id="summary")
                        with Horizontal(id="actions"):
                            yield Button("Write Setup", variant="primary", id="submit")
                            yield Button("Cancel", variant="default", id="cancel")
            yield Footer()

        def on_mount(self) -> None:
            self._update_summary()

        @on(Input.Changed)
        @on(Select.Changed)
        @on(Switch.Changed)
        def _changed(self) -> None:
            self._update_summary()

        @on(Button.Pressed, "#cancel")
        def _cancel(self) -> None:
            self.exit(None)

        @on(Button.Pressed, "#submit")
        def _submit(self) -> None:
            selected_model = str(self.query_one("#model", Select).value)
            custom_model = self.query_one("#custom_model", Input).value.strip()
            profile = str(self.query_one("#profile", Select).value)
            options = SetupOptions(
                openrouter_api_key=self.query_one("#openrouter_key", Input).value.strip(),
                default_model=custom_model or selected_model,
                stack_profile=profile,
                telemetry_enabled=bool(self.query_one("#telemetry", Switch).value) or profile == "full",
                no_docker=not bool(self.query_one("#docker", Switch).value),
                no_onboard=not bool(self.query_one("#create_agent", Switch).value),
            )
            self.exit(
                SetupWizardResult(
                    options=options,
                    create_first_agent=bool(self.query_one("#create_agent", Switch).value),
                )
            )

        def _update_summary(self) -> None:
            selected_model = str(self.query_one("#model", Select).value)
            custom_model = self.query_one("#custom_model", Input).value.strip()
            profile = str(self.query_one("#profile", Select).value)
            model = custom_model or selected_model
            docker = "yes" if self.query_one("#docker", Switch).value else "no"
            telemetry = "yes" if self.query_one("#telemetry", Switch).value or profile == "full" else "no"
            create_agent = "yes" if self.query_one("#create_agent", Switch).value else "no"
            self.query_one("#summary", Static).update(
                "\n".join(
                    [
                        f"Model: {model}",
                        f"Profile: {profile}",
                        f"Start Docker: {docker}",
                        f"Telemetry: {telemetry}",
                        f"Launch Brain Clone next: {create_agent}",
                    ]
                )
            )

    result = SetupApp().run()
    if result is None:
        raise KeyboardInterrupt
    return result
