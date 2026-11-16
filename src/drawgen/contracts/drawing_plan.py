"""DrawingPlan and PlanSelection (HANDOFF.md section 8.9).

NFR-02: neither model has a field that can hold a dimension value. The only
numbers are the plan version and layout numbers (sheet size, view scale and
centre, placement rank, note anchor). tests/contract/test_nfr02.py enforces
this with an exact allow-list; changing it needs a decision note.
"""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import Contract, Placement, Projection, Pt2, SheetSize


class PlanView(Contract):
    id: str
    candidate_id: str
    scale: float
    center: Pt2


class PlanDimension(Contract):
    id: str
    candidate_id: str
    view_id: str
    scheme_group: str | None = None
    placement: Placement


class PlanNote(Contract):
    id: str
    text: str
    anchor: Pt2
    source: Literal["reference_convention", "requirement_doc", "human"]
    flagged: bool


class TitleBlockEntry(Contract):
    value: str
    source: str


class ReviewFlag(Contract):
    id: str
    kind: str
    message: str
    refs: list[str] = Field(default_factory=list)


class PlanProvenance(Contract):
    planner: Literal["rules", "llm", "human"]
    model: str | None = None
    prompt_hash: str | None = None


class DrawingPlan(Contract):
    schema_: Literal["drawing_plan/0"] = Field("drawing_plan/0", alias="schema")
    plan_version: int
    target_hash: str
    pack: str
    template: str | None
    sheet: SheetSize
    standard: str | None
    projection: Projection | None
    views: list[PlanView]
    dimensions: list[PlanDimension]
    notes: list[PlanNote] = Field(default_factory=list)
    title_block: dict[str, TitleBlockEntry] = Field(default_factory=dict)
    review_flags: list[ReviewFlag] = Field(default_factory=list)
    provenance: PlanProvenance


class DimensionChoice(Contract):
    candidate_id: str
    view_candidate_id: str


class RoleAssignment(Contract):
    feature_id: str
    role: str


class PlanSelection(Contract):
    """The only thing an LLM may return for planning. IDs only, no numbers."""

    schema_: Literal["plan_selection/0"] = Field("plan_selection/0", alias="schema")
    view_candidate_ids: list[str] = Field(default_factory=list)
    dimension_choices: list[DimensionChoice] = Field(default_factory=list)
    role_assignments: list[RoleAssignment] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
