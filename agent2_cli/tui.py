"""Textual Brain Clone onboarding workbench."""

from __future__ import annotations

from agent2_cli.spec import (
    AgentIdentity,
    AgentSpec,
    ExampleCaseSpec,
    KnowledgeCollectionSpec,
    OutcomeSpec,
    SchemaFieldSpec,
    ToolSpec,
)


def run_brain_clone_tui() -> AgentSpec:
    """Run the fullscreen Textual onboarding app and return an AgentSpec."""

    from textual import on
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, VerticalScroll
    from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Static

    class BrainCloneApp(App[AgentSpec]):
        CSS = """
        Screen {
            background: #1A1A1A;
            color: #ffffff;
        }

        #shell {
            height: 100%;
        }

        #hero {
            height: 5;
            padding: 1 2;
            background: #151515;
            border-bottom: tall #2A2A2A;
        }

        #brand {
            text-style: bold;
            color: #ffffff;
        }

        #subtitle {
            color: #9A9590;
        }

        #body {
            height: 1fr;
        }

        #rail {
            width: 31;
            padding: 1 2;
            background: #0D0D0D;
            border-right: tall #2A2A2A;
        }

        .rail-title {
            color: #ffffff;
            text-style: bold;
            margin-bottom: 1;
        }

        .rail-item {
            height: 3;
            padding: 0 1;
            color: #777777;
        }

        .rail-item-active {
            color: #ffffff;
            background: #1A1A1A;
            text-style: bold;
        }

        #workspace {
            width: 1fr;
            padding: 1 2;
        }

        #stage-title {
            text-style: bold;
            color: #ffffff;
        }

        #stage-help {
            color: #9A9590;
            margin-bottom: 1;
        }

        #form {
            height: 1fr;
            border: tall #252525;
            background: #151515;
            padding: 1 2;
        }

        .stage {
            display: none;
        }

        .stage-active {
            display: block;
        }

        .section {
            margin: 1 0;
            color: #FF3B30;
            text-style: bold;
        }

        Label {
            margin-top: 1;
            color: #9A9590;
        }

        Input {
            margin-bottom: 1;
        }

        Checkbox {
            margin-top: 1;
        }

        #actions {
            height: 4;
            padding-top: 1;
        }

        Button {
            margin-right: 1;
            min-width: 16;
        }

        #status {
            color: #FF3B30;
            margin-top: 1;
        }

        #review {
            color: #9A9590;
            background: #0D0D0D;
            border: tall #2A2A2A;
            padding: 1 2;
            margin-top: 1;
        }
        """

        BINDINGS = [
            ("escape", "quit", "Quit"),
            ("ctrl+j", "next_stage", "Next"),
            ("ctrl+k", "previous_stage", "Back"),
        ]

        STAGES = [
            ("Start", "Name the expert and the desk they sit at."),
            ("Workspace", "Choose tools, books, and clarification behavior."),
            ("Chain", "Write the visible Sachbearbeiter Chain-of-Thought checkpoints."),
            ("Example", "Give one real case and the typed work product."),
            ("Review", "Check the generated blueprint before writing files."),
        ]

        stage_index = 0

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical(id="shell"):
                with Container(id="hero"):
                    yield Static("Agent2 Brain Clone", id="brand")
                    yield Static(
                        "Turn a domain expert into a sandbox-first Agent2 service.",
                        id="subtitle",
                    )
                with Horizontal(id="body"):
                    with Vertical(id="rail"):
                        yield Static("Onboarding", classes="rail-title")
                        for index, (title, _) in enumerate(self.STAGES):
                            yield Static(f"{index + 1}. {title}", id=f"rail_{index}", classes="rail-item")
                    with Vertical(id="workspace"):
                        yield Static("", id="stage-title")
                        yield Static("", id="stage-help")
                        with VerticalScroll(id="form"):
                            with Container(id="stage_0", classes="stage"):
                                yield Static("Expert identity", classes="section")
                                yield Label("Agent name")
                                yield Input(value="my-brain-clone", id="name")
                                yield Label("Professional role")
                                yield Input(value="Roofing estimator", id="role")
                                yield Label("Domain")
                                yield Input(value="roofing and building repair", id="domain")
                                yield Label("Years of experience")
                                yield Input(value="10", id="years")
                                yield Label("Case type")
                                yield Input(value="customer repair request", id="case_type")
                                yield Label("One-sentence agent description")
                                yield Input(
                                    value="Processes customer repair requests like an expert roofing estimator.",
                                    id="description",
                                )
                                yield Label("Expert mindset")
                                yield Input(
                                    value="Practical, safety-aware, detail-oriented, and never guesses.",
                                    id="mindset",
                                )
                            with Container(id="stage_1", classes="stage"):
                                yield Static("Workspace and tools", classes="section")
                                yield Checkbox("Agent may ask humans for missing information", True, id="clarify")
                                yield Checkbox("Create a knowledge collection for books and manuals", True, id="use_books")
                                yield Label("Knowledge collection slug")
                                yield Input(value="my-brain-clone-books", id="collection_name")
                                yield Label("Knowledge collection description")
                                yield Input(
                                    value="Reference books and documents for this expert.",
                                    id="collection_desc",
                                )
                                yield Static("Default tools", classes="section")
                                yield Static("lookup_case_context, update_case_memory, optional clarification action")
                            with Container(id="stage_2", classes="stage"):
                                yield Static("Sachbearbeiter Chain-of-Thought", classes="section")
                                yield Label("Checkpoint 1")
                                yield Input(value="What landed on my desk?", id="step_1")
                                yield Label("Checkpoint 2")
                                yield Input(value="What context or history do I need?", id="step_2")
                                yield Label("Checkpoint 3")
                                yield Input(value="Which rules, constraints, or safety issues apply?", id="step_3")
                                yield Label("Checkpoint 4")
                                yield Input(value="What is missing or unclear?", id="step_4")
                                yield Label("Checkpoint 5")
                                yield Input(value="Can I complete, clarify, or reject this case?", id="step_5")
                            with Container(id="stage_3", classes="stage"):
                                yield Static("Example and output contract", classes="section")
                                yield Label("Typical case")
                                yield Input(value="A normal customer repair request with enough details.", id="typical_case")
                                yield Label("Expert chain for that case")
                                yield Input(
                                    value="Classify the request, inspect context, check constraints, then complete the work product.",
                                    id="example_thought",
                                )
                                yield Label("Final work product")
                                yield Input(value="Structured expert work product.", id="output_desc")
                            with Container(id="stage_4", classes="stage"):
                                yield Static("Review", classes="section")
                                yield Static("", id="review")
                                yield Static("", id="status")
                        with Horizontal(id="actions"):
                            yield Button("Back", variant="default", id="back")
                            yield Button("Next", variant="primary", id="next")
                            yield Button("Generate Agent", variant="success", id="generate")
                            yield Button("Cancel", variant="default", id="cancel")
            yield Footer()

        def on_mount(self) -> None:
            self._render_stage()

        def action_next_stage(self) -> None:
            self._next()

        def action_previous_stage(self) -> None:
            self._previous()

        @on(Button.Pressed, "#back")
        def _previous_pressed(self) -> None:
            self._previous()

        @on(Button.Pressed, "#next")
        def _next_pressed(self) -> None:
            self._next()

        @on(Button.Pressed, "#cancel")
        def _cancel(self) -> None:
            self.exit(None)

        @on(Button.Pressed, "#generate")
        def _generate(self) -> None:
            try:
                self.exit(self._build_spec())
            except Exception as exc:
                self.query_one("#status", Static).update(str(exc))

        def _previous(self) -> None:
            if self.stage_index > 0:
                self.stage_index -= 1
                self._render_stage()

        def _next(self) -> None:
            if self.stage_index < len(self.STAGES) - 1:
                self.stage_index += 1
                self._render_stage()

        def _render_stage(self) -> None:
            for index, (title, help_text) in enumerate(self.STAGES):
                rail = self.query_one(f"#rail_{index}", Static)
                rail.set_class(index == self.stage_index, "rail-item-active")
                stage = self.query_one(f"#stage_{index}", Container)
                stage.set_class(index == self.stage_index, "stage-active")
            title, help_text = self.STAGES[self.stage_index]
            self.query_one("#stage-title", Static).update(f"{self.stage_index + 1}/{len(self.STAGES)}  {title}")
            self.query_one("#stage-help", Static).update(help_text)
            self.query_one("#back", Button).disabled = self.stage_index == 0
            self.query_one("#next", Button).display = self.stage_index < len(self.STAGES) - 1
            self.query_one("#generate", Button).display = self.stage_index == len(self.STAGES) - 1
            if self.stage_index == len(self.STAGES) - 1:
                self._update_review()

        def _value(self, widget_id: str) -> str:
            return self.query_one(f"#{widget_id}", Input).value.strip()

        def _update_review(self) -> None:
            try:
                spec = self._build_spec()
            except Exception as exc:
                self.query_one("#review", Static).update(f"Cannot generate yet:\n{exc}")
                return
            self.query_one("#review", Static).update(
                "\n".join(
                    [
                        f"Agent: {spec.name}",
                        f"Role: {spec.identity.role} in {spec.identity.domain}",
                        f"Case type: {spec.case_type}",
                        f"Tools: {', '.join(tool.name for tool in spec.tools) or 'none'}",
                        f"Books: {', '.join(collection.name for collection in spec.knowledge_collections) or 'none'}",
                        f"Outcomes: {', '.join(outcome.name for outcome in spec.outcomes)}",
                    ]
                )
            )

        def _build_spec(self) -> AgentSpec:
            years = int(self._value("years") or "0")
            tools = [
                ToolSpec(
                    name="lookup_case_context",
                    description="Look up customer, site, or case context.",
                    category="context",
                ),
                ToolSpec(
                    name="update_case_memory",
                    description="Update memory with learnings from this case.",
                    category="memory",
                ),
            ]
            if self.query_one("#clarify", Checkbox).value:
                tools.append(
                    ToolSpec(
                        name="send_clarification_request",
                        description="Draft a clarification request as a pending action.",
                        category="communication",
                        sandbox=True,
                    )
                )
            collection_name = self._value("collection_name")
            knowledge_collections = []
            if self.query_one("#use_books", Checkbox).value and collection_name:
                knowledge_collections.append(
                    KnowledgeCollectionSpec(
                        name=collection_name,
                        description=self._value("collection_desc") or "Reference books and documents.",
                        books_dir=f"knowledge/books/{collection_name}",
                    )
                )
            return AgentSpec(
                name=self._value("name"),
                description=self._value("description"),
                identity=AgentIdentity(
                    role=self._value("role"),
                    domain=self._value("domain"),
                    years_experience=years,
                    mindset=self._value("mindset"),
                ),
                case_type=self._value("case_type"),
                chain_of_thought_steps=[
                    self._value("step_1"),
                    self._value("step_2"),
                    self._value("step_3"),
                    self._value("step_4"),
                    self._value("step_5"),
                ],
                tools=tools,
                knowledge_collections=knowledge_collections,
                outcomes=[
                    OutcomeSpec(name="complete", description="The expert can finish the work product."),
                    OutcomeSpec(name="needs_clarification", description="A human must provide missing facts."),
                    OutcomeSpec(name="rejected", description="The input is defective or unusable."),
                ],
                output_fields=[
                    SchemaFieldSpec(
                        name="domain_output",
                        type="dict",
                        description=self._value("output_desc"),
                        required=False,
                    )
                ],
                example_cases=[
                    ExampleCaseSpec(
                        title="Typical case",
                        input_summary=self._value("typical_case"),
                        chain_of_thought=self._value("example_thought"),
                        outcome="complete",
                    )
                ],
            )

    result = BrainCloneApp().run()
    if result is None:
        raise KeyboardInterrupt
    return result
