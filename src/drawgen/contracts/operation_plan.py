"""Contracts for plan-driven Branch C operations.

These models describe planning and evidence. They do not execute NXOpen calls.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from drawgen.contracts.common import Contract

PlanComplexity = Literal["simple", "complex", "ambiguous"]
PlanStepStatus = Literal["pending", "ready", "running", "completed", "failed", "skipped"]
CandidateKind = Literal[
    "class",
    "constructor",
    "method",
    "property",
    "field",
    "enumeration",
    "structure",
    "interface",
]
CandidateStatus = Literal["unvalidated", "validated", "rejected", "unavailable"]
PipelineStatus = Literal["pending", "running", "succeeded", "failed", "needs_clarification"]


class PlanStep(Contract):
    """One ordered, deterministic step in an assistant operation plan."""

    id: str
    action: str
    description: str
    status: PlanStepStatus = "pending"
    entity_requirements: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    api_queries: list[str] = Field(default_factory=list)
    api_candidate_ids: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    unit: str | None = None
    fallback_step_ids: list[str] = Field(default_factory=list)


class ApiCandidate(Contract):
    """Evidence for one API or property considered for a plan step."""

    id: str
    query: str
    kind: CandidateKind
    full_name: str
    summary: str = ""
    signature: str | None = None
    guid: str | None = None
    assembly: str | None = None
    source: str | None = None
    nx_version: str | None = None
    status: CandidateStatus = "unvalidated"
    validation_message: str | None = None


class PipelineStep(Contract):
    """A validated plan step mapped to a typed assistant tool."""

    id: str
    plan_step_id: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    api_candidate_id: str | None = None
    requires_confirmation: bool = False
    expected_outputs: list[str] = Field(default_factory=list)


class OperationPlan(Contract):
    """The clarified goal and ordered work required for one assistant turn."""

    schema_: Literal["operation_plan/0"] = Field("operation_plan/0", alias="schema")
    request: str
    goal: str
    complexity: PlanComplexity
    clarification_required: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    api_candidates: list[ApiCandidate] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)


class PipelineResult(Contract):
    """Execution evidence returned after a composed pipeline runs."""

    schema_: Literal["pipeline_result/0"] = Field("pipeline_result/0", alias="schema")
    pipeline_id: str
    plan_id: str | None = None
    status: PipelineStatus
    completed_steps: list[str] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    failed_candidate_ids: list[str] = Field(default_factory=list)
