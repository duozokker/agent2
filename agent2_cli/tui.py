"""Textual Brain Clone onboarding form."""

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
    """Run the Textual onboarding app and return an AgentSpec."""

    from textual import on
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, VerticalScroll
    from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Static

    class BrainCloneApp(App[AgentSpec]):
        CSS = """
        Screen {
            background: #101418;
        }

        #form {
            width: 86;
            max-width: 100%;
            margin: 1 2;
        }

        .section {
            margin-top: 1;
            color: #f0c674;
            text-style: bold;
        }

        Input {
            margin-bottom: 1;
        }

        #status {
            margin-top: 1;
            color: #ff6b6b;
        }

        Button {
            margin-top: 1;
            margin-right: 1;
        }
        """

        BINDINGS = [("escape", "quit", "Quit")]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with VerticalScroll(id="form"):
                yield Static("Agent2 Brain Clone", classes="section")
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
                yield Label("Description")
                yield Input(value="Processes customer repair requests like an expert roofing estimator.", id="description")
                yield Label("Expert mindset")
                yield Input(value="Practical, safety-aware, detail-oriented, and never guesses.", id="mindset")

                yield Static("Sachbearbeiter Chain-of-Thought", classes="section")
                yield Label("Step 1")
                yield Input(value="What landed on my desk?", id="step_1")
                yield Label("Step 2")
                yield Input(value="What context or history do I need?", id="step_2")
                yield Label("Step 3")
                yield Input(value="Which rules, constraints, or safety issues apply?", id="step_3")
                yield Label("Step 4")
                yield Input(value="What is missing or unclear?", id="step_4")
                yield Label("Step 5")
                yield Input(value="Can I complete, clarify, or reject this case?", id="step_5")

                yield Static("Tools, Example, Output", classes="section")
                yield Checkbox("Agent may ask humans for missing information", True, id="clarify")
                yield Label("Knowledge collection slug")
                yield Input(value="my-brain-clone-books", id="collection_name")
                yield Label("Knowledge collection description")
                yield Input(value="Reference books and documents for this expert.", id="collection_desc")
                yield Label("Typical case")
                yield Input(value="A normal customer repair request with enough details.", id="typical_case")
                yield Label("Expert chain for that case")
                yield Input(
                    value="Classify the request, inspect context, check constraints, then complete the work product.",
                    id="example_thought",
                )
                yield Label("Final work product")
                yield Input(value="Structured expert work product.", id="output_desc")
                with Horizontal():
                    yield Button("Generate Agent", variant="primary", id="generate")
                    yield Button("Cancel", variant="default", id="cancel")
                yield Static("", id="status")
            yield Footer()

        def _value(self, widget_id: str) -> str:
            return self.query_one(f"#{widget_id}", Input).value.strip()

        @on(Button.Pressed, "#cancel")
        def _cancel(self) -> None:
            self.exit(None)

        @on(Button.Pressed, "#generate")
        def _generate(self) -> None:
            try:
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
                if collection_name:
                    knowledge_collections.append(
                        KnowledgeCollectionSpec(
                            name=collection_name,
                            description=self._value("collection_desc") or "Reference books and documents.",
                            books_dir=f"knowledge/books/{collection_name}",
                        )
                    )
                spec = AgentSpec(
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
            except Exception as exc:
                self.query_one("#status", Static).update(str(exc))
                return
            self.exit(spec)

    result = BrainCloneApp().run()
    if result is None:
        raise KeyboardInterrupt
    return result
