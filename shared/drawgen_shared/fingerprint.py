"""JSON-ready geometry fingerprints and tolerant matching."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, cast

from .tolerances import DEFAULT, Tolerances
from .vec import Vec3, as_vec3, bbox_of_points, distance, is_parallel, midpoint, normalize

GeomKind = Literal[
    "plane",
    "cylinder",
    "cone",
    "sphere",
    "torus",
    "line",
    "circle",
    "arc",
    "other",
]


class Fingerprint(TypedDict):
    """JSON-shaped identity data for one face or edge."""

    kind: Literal["face", "edge"]
    geom: GeomKind
    size: float
    centroid: list[float]
    direction: list[float] | None
    radius: float | None
    bbox: list[float]
    component_path: str | None


@dataclass(frozen=True)
class MatchResult:
    """Result of matching one fingerprint against candidate fingerprints."""

    status: Literal["match", "no_match", "ambiguous"]
    index: int | None
    indices: tuple[int, ...]


_GEOMETRIES = frozenset(
    {"plane", "cylinder", "cone", "sphere", "torus", "line", "circle", "arc", "other"}
)


def _finite_float(value: Any, name: str) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite float") from exc
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be a finite float")
    return converted


def _geometry(value: Any) -> GeomKind:
    if value not in _GEOMETRIES:
        raise ValueError(f"unsupported geometry kind: {value!r}")
    return cast(GeomKind, value)


def _vec_list(value: Any, name: str) -> list[float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a length-three sequence")
    try:
        converted = as_vec3(cast(Sequence[float], value))
    except ValueError as exc:
        raise ValueError(f"{name} must be a finite length-three vector") from exc
    return list(converted)


def _optional_vec_list(value: Any, name: str) -> list[float] | None:
    if value is None:
        return None
    return _vec_list(value, name)


def _bbox_list(value: Any) -> list[float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 6:
        raise ValueError("bbox must be a length-six sequence")
    try:
        converted = tuple(_finite_float(item, "bbox") for item in value)
    except TypeError as exc:
        raise ValueError("bbox must be a length-six sequence") from exc
    return list(converted)


def _circle_bbox(center: Vec3, radius: float, direction: Vec3) -> list[float]:
    """Return the full-circle box; using it for arcs is a conservative choice."""

    normal = normalize(direction)
    extents = tuple(
        abs(radius) * math.sqrt(max(0.0, 1.0 - component * component)) for component in normal
    )
    return [
        center[0] - extents[0],
        center[1] - extents[1],
        center[2] - extents[2],
        center[0] + extents[0],
        center[1] + extents[1],
        center[2] + extents[2],
    ]


def from_face(face: Mapping[str, Any], component_path: str | None = None) -> Fingerprint:
    """Build a JSON-ready fingerprint from a RawFace-shaped mapping."""

    return {
        "kind": "face",
        "geom": _geometry(face["geom"]),
        "size": _finite_float(face["area"], "area"),
        "centroid": _vec_list(face["centroid"], "centroid"),
        "direction": _optional_vec_list(face.get("direction"), "direction"),
        "radius": (None if face.get("radius") is None else _finite_float(face["radius"], "radius")),
        "bbox": _bbox_list(face["bbox"]),
        "component_path": component_path,
    }


def from_edge(edge: Mapping[str, Any], component_path: str | None = None) -> Fingerprint:
    """Build a JSON-ready fingerprint from a RawEdge-shaped mapping.

    Circle and arc edges use the full-circle axis-aligned box as a conservative
    bounding box, since an arc's endpoints alone may not describe its extent.
    """

    geometry = _geometry(edge["geom"])
    start = None if edge.get("start") is None else as_vec3(cast(Sequence[float], edge["start"]))
    end = None if edge.get("end") is None else as_vec3(cast(Sequence[float], edge["end"]))
    center = None if edge.get("center") is None else as_vec3(cast(Sequence[float], edge["center"]))

    if center is not None:
        centroid = center
    elif start is not None and end is not None:
        centroid = midpoint(start, end)
    else:
        raise ValueError("an edge needs a center or both start and end points for its centroid")

    direction = (
        None if edge.get("direction") is None else as_vec3(cast(Sequence[float], edge["direction"]))
    )
    radius = None if edge.get("radius") is None else _finite_float(edge["radius"], "radius")
    if radius is not None and radius < 0.0:
        raise ValueError("radius must be non-negative")

    if (
        geometry in ("circle", "arc")
        and center is not None
        and radius is not None
        and direction is not None
    ):
        bbox = _circle_bbox(center, radius, direction)
    else:
        points = [point for point in (start, end, center) if point is not None]
        if not points:
            raise ValueError("an edge needs at least one point for its bounding box")
        bbox = list(bbox_of_points(points))

    return {
        "kind": "edge",
        "geom": geometry,
        "size": _finite_float(edge["length"], "length"),
        "centroid": list(centroid),
        "direction": None if direction is None else list(direction),
        "radius": radius,
        "bbox": bbox,
        "component_path": component_path,
    }


def _size_matches(a: float, b: float, tol: Tolerances) -> bool:
    difference = abs(a - b)
    relative_limit = tol.fingerprint_size_rel * max(abs(a), abs(b))
    return difference <= relative_limit or difference <= tol.fingerprint_size_abs


def _optional_radius_matches(
    a: float | None,
    b: float | None,
    tolerance: float,
) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tolerance


def is_same(a: Fingerprint, b: Fingerprint, tol: Tolerances = DEFAULT) -> bool:
    """Return whether two fingerprints describe the same geometric entity."""

    if a["kind"] != b["kind"] or a["geom"] != b["geom"]:
        return False
    if not _size_matches(a["size"], b["size"], tol):
        return False
    if distance(as_vec3(a["centroid"]), as_vec3(b["centroid"])) > tol.fingerprint_centroid_mm:
        return False

    direction_a = a["direction"]
    direction_b = b["direction"]
    if direction_a is None or direction_b is None:
        if direction_a is not None or direction_b is not None:
            return False
    else:
        try:
            if not is_parallel(
                as_vec3(direction_a),
                as_vec3(direction_b),
                tol.fingerprint_direction_rad,
                ignore_sign=True,
            ):
                return False
        except ValueError:
            return False

    return _optional_radius_matches(a["radius"], b["radius"], tol.fingerprint_radius_mm)


def match(
    fp: Fingerprint,
    candidates: Iterable[Fingerprint],
    tol: Tolerances = DEFAULT,
) -> MatchResult:
    """Match a fingerprint and report no, one, or multiple matching indices."""

    indices = tuple(
        index for index, candidate in enumerate(candidates) if is_same(fp, candidate, tol)
    )
    if not indices:
        return MatchResult(status="no_match", index=None, indices=())
    if len(indices) == 1:
        return MatchResult(status="match", index=indices[0], indices=indices)
    return MatchResult(status="ambiguous", index=None, indices=indices)
