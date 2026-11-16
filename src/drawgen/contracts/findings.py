"""Findings and the closed set of edits (HANDOFF.md section 8.11)."""

from typing import Annotated, Literal

from pydantic import Field

from drawgen.contracts.common import Contract, Pt2, Side


class MoveDimension(Contract):
    op: Literal["move_dimension"] = "move_dimension"
    id: str
    side: Side
    rank: int


class MoveView(Contract):
    op: Literal["move_view"] = "move_view"
    id: str
    center: Pt2


class SetViewScale(Contract):
    op: Literal["set_view_scale"] = "set_view_scale"
    id: str
    scale: float


class SetSheet(Contract):
    op: Literal["set_sheet"] = "set_sheet"
    width: float
    height: float


class AddDimension(Contract):
    op: Literal["add_dimension"] = "add_dimension"
    candidate_id: str
    view_id: str


class RemoveDimension(Contract):
    op: Literal["remove_dimension"] = "remove_dimension"
    id: str


class SwitchView(Contract):
    op: Literal["switch_view"] = "switch_view"
    dimension_id: str
    view_id: str


class AddView(Contract):
    op: Literal["add_view"] = "add_view"
    candidate_id: str


class Flag(Contract):
    op: Literal["flag"] = "flag"
    message: str
    refs: list[str] = Field(default_factory=list)


# Closed set: the repair loop may use nothing else.
Edit = Annotated[
    MoveDimension
    | MoveView
    | SetViewScale
    | SetSheet
    | AddDimension
    | RemoveDimension
    | SwitchView
    | AddView
    | Flag,
    Field(discriminator="op"),
]

FindingStatus = Literal["pass", "fail", "warn", "review"]


class FindingResult(Contract):
    rule_id: str
    status: FindingStatus
    message: str
    refs: list[str] = Field(default_factory=list)
    edits: list[Edit] = Field(default_factory=list)


class FindingsSummary(Contract):
    pass_: int = Field(0, alias="pass")
    fail: int = 0
    warn: int = 0
    review: int = 0


class Findings(Contract):
    schema_: Literal["findings/0"] = Field("findings/0", alias="schema")
    plan_version: int
    results: list[FindingResult]
    summary: FindingsSummary
