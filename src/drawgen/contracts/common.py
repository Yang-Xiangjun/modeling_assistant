"""Common types shared by all contracts (HANDOFF.md section 8.1). No logic."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Vec3 = tuple[float, float, float]
Pt2 = tuple[float, float]  # sheet mm, origin bottom-left, y up
BBox3 = tuple[float, float, float, float, float, float]  # xmin ymin zmin xmax ymax zmax
BBox2 = tuple[float, float, float, float]  # x0 y0 x1 y1
Mat3 = tuple[float, float, float, float, float, float, float, float, float]  # row-major
Mat4 = tuple[
    float, float, float, float,
    float, float, float, float,
    float, float, float, float,
    float, float, float, float,
]  # row-major  # fmt: skip

FaceGeom = Literal["plane", "cylinder", "cone", "sphere", "torus", "other"]
EdgeGeom = Literal["line", "circle", "arc", "other"]
GeomKind = Literal[
    "plane", "cylinder", "cone", "sphere", "torus", "line", "circle", "arc", "other"
]  # fmt: skip
Projection = Literal["first", "third"]
ViewKind = Literal["base", "projected", "section", "detail", "isometric", "other"]
DimKind = Literal[
    "linear", "diameter", "radius", "angular", "ordinate", "hole_callout", "chamfer", "other"
]
DimDirection = Literal["horizontal", "vertical", "parallel", "perpendicular"]
PointKind = Literal["end", "mid", "center", "tangent", "intersection"]
FrameDirection = Literal["+X", "-X", "+Y", "-Y", "+Z", "-Z", "iso"]
Side = Literal["above", "below", "left", "right"]
Scheme = Literal["ordinate", "baseline", "chain", "single", "callout", "table"]
ExportFormat = Literal["pdf", "dxf"]

ParamScalar = bool | int | float | str
ParamValue = ParamScalar | list[ParamScalar]


class Contract(BaseModel):
    """Base for every contract model.

    Unknown fields are rejected, NaN and infinity are rejected, and JSON always
    uses the alias names (for example ``schema``).
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
        allow_inf_nan=False,
        protected_namespaces=(),
    )


class Fingerprint(Contract):
    """Re-finds one face or edge in the same model across sessions."""

    kind: Literal["face", "edge"]
    geom: GeomKind
    size: float  # area for a face, length for an edge
    centroid: Vec3  # model absolute
    direction: Vec3 | None = None
    radius: float | None = None
    bbox: BBox3
    component_path: str | None = None  # hint only, never required for a match


class Tolerances(Contract):
    """The one tolerance config object (HANDOFF.md sections 7 and 8.1)."""

    linear_mm: float = 0.001
    angular_deg: float = 0.01
    fingerprint_size_rel: float = 1e-6
    fingerprint_size_abs: float = 1e-4
    fingerprint_centroid_mm: float = 0.001
    fingerprint_direction_rad: float = 1e-4
    fingerprint_radius_mm: float = 0.001


class SheetSize(Contract):
    width: float
    height: float


class Placement(Contract):
    side: Side
    rank: int


class FeatureRef(Contract):
    feature_id: str
    entity: str  # "axis", "face:top", "edge:min_x", ...
