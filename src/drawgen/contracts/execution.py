"""ExecutionJob and ExecutionReport: worker input and output (HANDOFF.md section 8.10)."""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import (
    BBox2,
    Contract,
    DimDirection,
    DimKind,
    ExportFormat,
    Fingerprint,
    Mat3,
    PointKind,
    Projection,
    Pt2,
    ViewKind,
)


class JobSheet(Contract):
    width: float
    height: float
    scale: float
    projection: Projection | None
    standard: str | None


class JobView(Contract):
    id: str
    kind: ViewKind
    parent_id: str | None = None
    rotation: Mat3
    scale: float
    center: Pt2
    representation: Literal["exact"] = "exact"


class JobAttachment(Contract):
    fingerprint: Fingerprint
    point_kind: PointKind | None = None


class JobDimension(Contract):
    id: str
    view_id: str
    dim_kind: DimKind
    direction: DimDirection | None
    attachments: list[JobAttachment]
    origin: Pt2
    scheme_group: str | None = None


class JobNote(Contract):
    id: str
    text: str
    origin: Pt2


class ExecutionJob(Contract):
    schema_: Literal["execution_job/0"] = Field("execution_job/0", alias="schema")
    plan_version: int
    target_part: str
    template: str | None
    output_drawing: str
    sheet: JobSheet
    views: list[JobView]
    dimensions: list[JobDimension]
    notes: list[JobNote] = Field(default_factory=list)
    title_block: dict[str, str] = Field(default_factory=dict)
    export: list[ExportFormat] = Field(default_factory=list)


class ReportView(Contract):
    id: str
    created: bool
    error: str | None = None
    name: str | None = None
    bbox: BBox2 | None = None
    scale: float | None = None
    out_of_date: bool | None = None


class ReportDimension(Contract):
    id: str
    created: bool
    error: str | None = None
    value: float | None = None
    text: str | None = None
    associative: bool | None = None
    retained: bool | None = None
    bbox: BBox2 | None = None


class UnresolvedAttachment(Contract):
    dimension_id: str
    attachment_index: int
    reason: Literal["no_match", "ambiguous", "not_visible_in_view"]


class ExportedFile(Contract):
    format: ExportFormat
    path: str


class ExecutionReport(Contract):
    schema_: Literal["execution_report/0"] = Field("execution_report/0", alias="schema")
    plan_version: int
    drawing_part: str | None
    nx_version: str | None
    saved: bool
    views: list[ReportView]
    dimensions: list[ReportDimension]
    unresolved: list[UnresolvedAttachment] = Field(default_factory=list)
    exports: list[ExportedFile] = Field(default_factory=list)
