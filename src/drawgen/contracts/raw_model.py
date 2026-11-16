"""Worker output: RawModel (HANDOFF.md section 8.2)."""

from typing import Literal

from pydantic import Field

from drawgen.contracts.common import BBox3, Contract, EdgeGeom, FaceGeom, Mat4, Vec3


class RawModelSource(Contract):
    path: str
    units: Literal["mm"] = "mm"
    nx_version: str | None
    extracted_at: str  # ISO 8601
    synthetic: bool
    attributes: dict[str, str] = Field(default_factory=dict)


class RawComponent(Contract):
    id: str
    parent_id: str | None
    name: str
    part_name: str
    attributes: dict[str, str] = Field(default_factory=dict)
    transform: Mat4 | None = None
    suppressed: bool = False


class RawFace(Contract):
    id: str
    geom: FaceGeom
    area: float
    centroid: Vec3
    direction: Vec3 | None = None
    axis_point: Vec3 | None = None
    radius: float | None = None
    half_angle: float | None = None
    convex: bool | None = None  # tells a boss from a hole; None when the worker cannot tell
    bbox: BBox3
    edge_ids: list[str] = Field(default_factory=list)


class RawEdge(Contract):
    id: str
    geom: EdgeGeom
    length: float
    start: Vec3 | None = None
    end: Vec3 | None = None
    center: Vec3 | None = None
    direction: Vec3 | None = None
    radius: float | None = None
    face_ids: list[str] = Field(default_factory=list)


class RawBody(Contract):
    id: str
    component_id: str
    kind: Literal["solid", "sheet"]
    bbox: BBox3
    volume: float | None = None
    faces: list[RawFace] = Field(default_factory=list)
    edges: list[RawEdge] = Field(default_factory=list)


class RawModel(Contract):
    schema_: Literal["raw_model/0"] = Field("raw_model/0", alias="schema")
    source: RawModelSource
    components: list[RawComponent]  # flat, one per occurrence, root included
    bodies: list[RawBody]
