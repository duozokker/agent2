"""Pydantic specs used by the Agent2 Brain Clone onboarding harness."""

from __future__ import annotations

import re
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")


class AgentIdentity(BaseModel):
    role: str = Field(description="Professional role being cloned")
    domain: str = Field(description="Domain or industry")
    years_experience: int = Field(default=10, ge=0, le=80)
    mindset: str = Field(default="Thorough when needed, efficient when possible, never guesses.")


class ToolSpec(BaseModel):
    name: str = Field(description="Python-safe tool name")
    description: str
    category: Literal["context", "memory", "knowledge", "web", "communication", "record", "other"] = "other"
    sandbox: bool = False

    @field_validator("name")
    @classmethod
    def _tool_name_is_identifier(cls, value: str) -> str:
        if not value.isidentifier():
            raise ValueError("tool names must be valid Python identifiers")
        return value


class KnowledgeCollectionSpec(BaseModel):
    name: str
    description: str
    books_dir: str = ""

    @field_validator("name")
    @classmethod
    def _collection_name_is_slug(cls, value: str) -> str:
        if not _SLUG_RE.fullmatch(value):
            raise ValueError("collection name must be kebab-case")
        return value


class OutcomeSpec(BaseModel):
    name: str
    description: str

    @field_validator("name")
    @classmethod
    def _outcome_name_is_identifier(cls, value: str) -> str:
        if not value.isidentifier():
            raise ValueError("outcome names must be Python-safe identifiers")
        return value


class SchemaFieldSpec(BaseModel):
    name: str
    type: Literal["str", "int", "float", "bool", "list[str]", "dict"] = "str"
    description: str
    required: bool = True

    @field_validator("name")
    @classmethod
    def _field_name_is_identifier(cls, value: str) -> str:
        if not value.isidentifier():
            raise ValueError("schema field names must be valid Python identifiers")
        return value


class ExampleCaseSpec(BaseModel):
    title: str
    input_summary: str
    chain_of_thought: str
    outcome: str


class AgentSpec(BaseModel):
    """Validated blueprint for deterministic Agent2 agent generation."""

    name: str = Field(description="Agent directory and service name, kebab-case")
    description: str
    identity: AgentIdentity
    case_type: str = "case"
    chain_of_thought_steps: list[str] = Field(min_length=3)
    tools: list[ToolSpec] = Field(default_factory=list)
    knowledge_collections: list[KnowledgeCollectionSpec] = Field(default_factory=list)
    outcomes: list[OutcomeSpec] = Field(default_factory=list)
    output_fields: list[SchemaFieldSpec] = Field(default_factory=list)
    example_cases: list[ExampleCaseSpec] = Field(default_factory=list)
    port: int = Field(default=8014, ge=1, le=65535)

    @field_validator("name")
    @classmethod
    def _name_is_slug(cls, value: str) -> str:
        if not _SLUG_RE.fullmatch(value):
            raise ValueError("agent name must be kebab-case")
        return value

    @model_validator(mode="after")
    def _has_canonical_outcomes(self) -> Self:
        if not self.outcomes:
            self.outcomes = [
                OutcomeSpec(name="complete", description="The expert can finish the work product."),
                OutcomeSpec(name="needs_clarification", description="A human must provide missing facts."),
                OutcomeSpec(name="rejected", description="The input is defective or unusable."),
            ]

        names = {outcome.name for outcome in self.outcomes}
        missing = {"needs_clarification", "rejected"} - names
        if missing:
            raise ValueError("outcomes must include needs_clarification and rejected")
        if len(self.outcomes) < 3:
            raise ValueError("at least three outcomes are required")
        return self


def class_name_from_slug(slug: str) -> str:
    """Convert ``roofing-estimator`` to ``RoofingEstimator``."""

    return "".join(part.capitalize() for part in re.split(r"[-_]+", slug) if part)
