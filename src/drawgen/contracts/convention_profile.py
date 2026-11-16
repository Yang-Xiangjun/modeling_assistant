"""ConventionProfile derived from a reference drawing (HANDOFF.md section 8.6)."""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import (
    Contract,
    DimKind,
    FrameDirection,
    Projection,
    Pt2,
    Scheme,
    SheetSize,
    Side,
    ViewKind,
)
from drawgen.contracts.raw_drawing import RawTolerance


class ProfileView(Contract):
    key: str
    kind: ViewKind
    direction_in_frame: FrameDirection | None
    parent_key: str | None = None
    scale: float
    anchor: Pt2  # normalised 0..1 on the sheet


class Selector(Contract):
    """Picks one coordinate source by role and entity, for example role + "min_x"."""

    role: str
    entity: str


class Datum(Contract):
    x_from: Selector
    y_from: Selector


class ProfileDimensionRule(Contract):
    role_signature: str
    dim_kind: DimKind
    scheme: Scheme
    view_key: str
    placement_side: Side | None
    observed: int
    example_raw_ids: list[str] = Field(default_factory=list)


class ProfileNote(Contract):
    text: str
    anchor: Pt2
    carry: Literal["flag"] = "flag"  # always carried as a review flag


class ToleranceSeen(Contract):
    """Recorded from the reference, never applied automatically (rule 2)."""

    role_signature: str
    tolerance: RawTolerance


class ConventionProfile(Contract):
    schema_: Literal["convention_profile/0"] = Field("convention_profile/0", alias="schema")
    reference_hash: str
    pack: str
    template: str | None
    sheet: SheetSize
    standard: str | None
    projection: Projection | None
    views: list[ProfileView]
    datum: Datum | None
    dimension_rules: list[ProfileDimensionRule]
    notes: list[ProfileNote] = Field(default_factory=list)
    tolerances_seen: list[ToleranceSeen] = Field(default_factory=list)
    unlinked_count: int
