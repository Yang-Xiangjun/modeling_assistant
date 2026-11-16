"""DrawingGraph: a RawDrawing linked to features (HANDOFF.md section 8.5)."""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import (
    Contract,
    DimDirection,
    DimKind,
    FeatureRef,
    FrameDirection,
    Projection,
    Side,
)
from drawgen.contracts.raw_drawing import AppendedText, RawNote, RawTable, RawTolerance, RawView


class GView(RawView):
    direction_in_frame: FrameDirection | None = None


class ObservedPlacement(Contract):
    """Placement as observed on a reference drawing; the side may be undeterminable."""

    side: Side | None
    rank: int


class GDimension(Contract):
    id: str
    raw_id: str
    view_id: str | None
    kind: DimKind
    direction: DimDirection | None = None
    value: float | None
    feature_refs: list[FeatureRef] = Field(default_factory=list)
    role_signature: str | None = None
    tolerance: RawTolerance | None = None
    appended_text: AppendedText | None = None
    placement: ObservedPlacement | None = None


class GSheet(Contract):
    id: str
    width: float
    height: float
    scale: float
    projection: Projection | None = None
    standard: str | None = None
    views: list[GView] = Field(default_factory=list)
    dimensions: list[GDimension] = Field(default_factory=list)
    notes: list[RawNote] = Field(default_factory=list)
    tables: list[RawTable] = Field(default_factory=list)


class UnlinkedDimension(Contract):
    dimension_id: str
    reason: str


class DrawingGraph(Contract):
    schema_: Literal["drawing_graph/0"] = Field("drawing_graph/0", alias="schema")
    drawing_hash: str
    model_hash: str
    sheets: list[GSheet]
    unlinked: list[UnlinkedDimension] = Field(default_factory=list)
