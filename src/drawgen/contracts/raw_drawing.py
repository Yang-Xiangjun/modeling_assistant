"""Worker output: RawDrawing (HANDOFF.md section 8.3)."""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import (
    BBox2,
    Contract,
    DimDirection,
    DimKind,
    Fingerprint,
    Mat3,
    PointKind,
    Projection,
    Pt2,
    Vec3,
    ViewKind,
)


class RawDrawingSource(Contract):
    path: str
    nx_version: str | None
    extracted_at: str  # ISO 8601
    synthetic: bool
    model_part: str | None  # None when the sheets live in the model part or it is unknown
    attributes: dict[str, str] = Field(default_factory=dict)


class RawView(Contract):
    id: str
    name: str
    kind: ViewKind
    parent_id: str | None = None
    model_view: str | None = None
    rotation: Mat3 | None = None  # model -> view
    scale: float
    center: Pt2
    bbox: BBox2
    representation: str | None = None
    out_of_date: bool | None = None


class AppendedText(Contract):
    before: str = ""
    after: str = ""
    above: str = ""
    below: str = ""


class RawTolerance(Contract):
    type: str
    upper: float | None = None
    lower: float | None = None


class RawAttachment(Contract):
    index: int
    entity_kind: Literal["face", "edge", "point", "centerline", "other"] | None = None
    fingerprint: Fingerprint | None = None  # the model entity, when it can be traced
    point: Vec3 | None = None
    point_kind: PointKind | None = None
    view_id: str | None = None
    trace_note: str | None = None  # why tracing failed, if it did


class RawDimension(Contract):
    id: str
    view_id: str | None
    kind: DimKind
    direction: DimDirection | None = None
    value: float | None  # the measurement as NX reports it
    text: str
    text_overridden: bool | None = None
    appended_text: AppendedText | None = None
    tolerance: RawTolerance | None = None
    origin: Pt2
    bbox: BBox2 | None = None
    retained: bool | None = None
    attachments: list[RawAttachment] = Field(default_factory=list)


class RawNote(Contract):
    id: str
    text: str
    origin: Pt2
    view_id: str | None = None
    has_leader: bool = False


class RawTable(Contract):
    id: str
    kind: Literal["hole_table", "parts_list", "tabular_note", "title_block", "other"]
    origin: Pt2
    rows: list[list[str]]


class RawSheet(Contract):
    id: str
    name: str
    width: float
    height: float
    scale: float
    projection: Projection | None = None
    standard: str | None = None
    views: list[RawView] = Field(default_factory=list)
    dimensions: list[RawDimension] = Field(default_factory=list)
    notes: list[RawNote] = Field(default_factory=list)
    tables: list[RawTable] = Field(default_factory=list)


class RawDrawing(Contract):
    schema_: Literal["raw_drawing/0"] = Field("raw_drawing/0", alias="schema")
    source: RawDrawingSource
    sheets: list[RawSheet]
