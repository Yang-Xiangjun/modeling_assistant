"""Generate deterministic synthetic PCBA model and drawing fixtures.

The generator deliberately uses only the raw contracts and small geometry
helpers.  It is a stand-in for the NX worker while the real NX fixtures are
being recorded.

Usage::

    uv run python tools/make_synthetic.py
    uv run python tools/make_synthetic.py --check
"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from drawgen_shared.fingerprint import from_edge, from_face
from drawgen_shared.jsonio import write_json

from drawgen.contracts.raw_drawing import (
    RawDimension,
    RawDrawing,
    RawSheet,
    RawView,
)
from drawgen.contracts.raw_model import RawModel

ROOT = Path(__file__).resolve().parent.parent
SYNTHETIC_ROOT = ROOT / "fixtures" / "synthetic"
FIXTURE_ROOT = SYNTHETIC_ROOT / "pcba"
EXTRACTED_AT = "2026-11-16T00:00:00Z"
IDENTITY_4 = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


@dataclass(frozen=True)
class MountingHole:
    """A plated or unplated mounting hole in board coordinates."""

    x: float
    y: float
    diameter: float


@dataclass(frozen=True)
class Via:
    """A small through-board via."""

    x: float
    y: float
    diameter: float


@dataclass(frozen=True)
class BoxComponent:
    """A rectangular component envelope."""

    refdes: str
    side: str
    x: float
    y: float
    size_x: float
    size_y: float
    height: float


@dataclass(frozen=True)
class Connector:
    """A connector body and a regular pin array."""

    refdes: str
    x: float
    y: float
    size_x: float
    size_y: float
    height: float
    pin_rows: int
    pin_cols: int
    pitch: float
    pin_diameter: float
    pin_length_above_body: float


@dataclass(frozen=True)
class SyntheticParams:
    """All dimensions and placements needed to make one synthetic PCBA."""

    name: str
    board_length: float
    board_width: float
    board_thickness: float
    mounting_holes: tuple[MountingHole, ...]
    vias: tuple[Via, ...]
    box_components: tuple[BoxComponent, ...]
    connectors: tuple[Connector, ...]


@dataclass(frozen=True)
class _Entity:
    """A generated model entity and the component name used in fingerprints."""

    component_name: str
    entity: Mapping[str, Any]


def _id_key(value: str) -> tuple[tuple[str, int], ...]:
    parts: list[tuple[str, int]] = []
    for piece in value.split("."):
        prefix = piece.rstrip("0123456789")
        suffix = piece[len(prefix) :]
        parts.append((prefix, int(suffix) if suffix else -1))
    return tuple(parts)


def _validate_params(params: SyntheticParams) -> None:
    if params.board_length <= 0 or params.board_width <= 0 or params.board_thickness <= 0:
        raise ValueError("board dimensions must be positive")
    if not params.mounting_holes:
        raise ValueError("at least one mounting hole is required")
    for hole in params.mounting_holes:
        _validate_hole(hole.x, hole.y, hole.diameter, params, "mounting hole")
        if hole.diameter <= 1.0:
            raise ValueError("mounting hole diameter must be greater than 1 mm")
    for via in params.vias:
        _validate_hole(via.x, via.y, via.diameter, params, "via")
        if not 0.0 < via.diameter < 1.0:
            raise ValueError("via diameter must be between 0 and 1 mm")
    refs: set[str] = set()
    for component in params.box_components:
        if component.side not in {"top", "bottom"}:
            raise ValueError(f"invalid component side: {component.side}")
        _validate_box(component.x, component.y, component.size_x, component.size_y, params)
        if component.height <= 0:
            raise ValueError("component height must be positive")
        if component.refdes in refs:
            raise ValueError(f"duplicate reference designator: {component.refdes}")
        refs.add(component.refdes)
    for connector in params.connectors:
        _validate_box(connector.x, connector.y, connector.size_x, connector.size_y, params)
        if connector.height <= 0 or connector.pin_rows < 1 or connector.pin_cols < 1:
            raise ValueError("connector dimensions and pin counts must be positive")
        if connector.pitch <= 0 or connector.pin_diameter <= 0:
            raise ValueError("connector pitch and pin diameter must be positive")
        if connector.pin_length_above_body <= 0:
            raise ValueError("connector pin length must be positive")
        if connector.refdes in refs:
            raise ValueError(f"duplicate reference designator: {connector.refdes}")
        refs.add(connector.refdes)
        pin_1_x, pin_1_y = _pin_position(connector, 0, 0)
        pin_n_x, pin_n_y = _pin_position(connector, connector.pin_cols - 1, connector.pin_rows - 1)
        if not (0.0 <= pin_1_x <= params.board_length and 0.0 <= pin_1_y <= params.board_width):
            raise ValueError("connector pin 1 is outside the board")
        if not (0.0 <= pin_n_x <= params.board_length and 0.0 <= pin_n_y <= params.board_width):
            raise ValueError("last connector pin is outside the board")


def _validate_hole(x: float, y: float, diameter: float, params: SyntheticParams, kind: str) -> None:
    radius = diameter / 2.0
    if diameter <= 0 or not (radius <= x <= params.board_length - radius):
        raise ValueError(f"{kind} does not fit in board length")
    if not (radius <= y <= params.board_width - radius):
        raise ValueError(f"{kind} does not fit in board width")


def _validate_box(
    x: float,
    y: float,
    size_x: float,
    size_y: float,
    params: SyntheticParams,
) -> None:
    if size_x <= 0 or size_y <= 0 or x < 0 or y < 0:
        raise ValueError("component dimensions and coordinates must be positive")
    if x + size_x > params.board_length or y + size_y > params.board_width:
        raise ValueError("component does not fit on board")


def _pin_position(connector: Connector, col: int, row: int) -> tuple[float, float]:
    """Return pin center; pin 1 is offset 2 mm from the connector origin."""

    offset = 2.0
    return (
        connector.x + offset + col * connector.pitch,
        connector.y + offset + row * connector.pitch,
    )


def _bbox(
    xmin: float,
    ymin: float,
    zmin: float,
    xmax: float,
    ymax: float,
    zmax: float,
) -> tuple[float, float, float, float, float, float]:
    return (xmin, ymin, zmin, xmax, ymax, zmax)


def _plane(
    face_id: str,
    area: float,
    centroid: tuple[float, float, float],
    direction: tuple[float, float, float],
    bbox: tuple[float, float, float, float, float, float],
    edge_ids: Iterable[str],
) -> dict[str, Any]:
    return {
        "id": face_id,
        "geom": "plane",
        "area": area,
        "centroid": centroid,
        "direction": direction,
        "axis_point": None,
        "radius": None,
        "half_angle": None,
        "convex": None,
        "bbox": bbox,
        "edge_ids": list(edge_ids),
    }


def _line(
    edge_id: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    face_ids: Iterable[str],
) -> dict[str, Any]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    direction = (dx / length, dy / length, dz / length)
    return {
        "id": edge_id,
        "geom": "line",
        "length": length,
        "start": start,
        "end": end,
        "center": None,
        "direction": direction,
        "radius": None,
        "face_ids": list(face_ids),
    }


def _circle(
    edge_id: str,
    center: tuple[float, float, float],
    radius: float,
    face_ids: Iterable[str],
) -> dict[str, Any]:
    return {
        "id": edge_id,
        "geom": "circle",
        "length": 2.0 * math.pi * radius,
        "start": None,
        "end": None,
        "center": center,
        "direction": (0.0, 0.0, 1.0),
        "radius": radius,
        "face_ids": list(face_ids),
    }


def _cylinder_face(
    face_id: str,
    center_x: float,
    center_y: float,
    zmin: float,
    zmax: float,
    radius: float,
    convex: bool,
    edge_ids: Iterable[str],
) -> dict[str, Any]:
    return {
        "id": face_id,
        "geom": "cylinder",
        "area": 2.0 * math.pi * radius * (zmax - zmin),
        "centroid": (center_x, center_y, (zmin + zmax) / 2.0),
        "direction": (0.0, 0.0, 1.0),
        "axis_point": (center_x, center_y, zmin),
        "radius": radius,
        "half_angle": None,
        "convex": convex,
        "bbox": _bbox(
            center_x - radius,
            center_y - radius,
            zmin,
            center_x + radius,
            center_y + radius,
            zmax,
        ),
        "edge_ids": list(edge_ids),
    }


def _box_geometry(
    body_id: str,
    component_id: str,
    xmin: float,
    ymin: float,
    zmin: float,
    xmax: float,
    ymax: float,
    zmax: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Make six outward-oriented planar faces and their twelve edges."""

    center_x = (xmin + xmax) / 2.0
    center_y = (ymin + ymax) / 2.0
    center_z = (zmin + zmax) / 2.0
    dx = xmax - xmin
    dy = ymax - ymin
    dz = zmax - zmin

    def f(number: int) -> str:
        return f"{body_id}.f{number}"

    def e(number: int) -> str:
        return f"{body_id}.e{number}"

    faces = [
        _plane(
            f(0),
            dx * dy,
            (center_x, center_y, zmin),
            (0.0, 0.0, -1.0),
            _bbox(xmin, ymin, zmin, xmax, ymax, zmin),
            [e(0), e(1), e(2), e(3)],
        ),
        _plane(
            f(1),
            dx * dy,
            (center_x, center_y, zmax),
            (0.0, 0.0, 1.0),
            _bbox(xmin, ymin, zmax, xmax, ymax, zmax),
            [e(4), e(5), e(6), e(7)],
        ),
        _plane(
            f(2),
            dy * dz,
            (xmin, center_y, center_z),
            (-1.0, 0.0, 0.0),
            _bbox(xmin, ymin, zmin, xmin, ymax, zmax),
            [e(0), e(4), e(8), e(9)],
        ),
        _plane(
            f(3),
            dx * dz,
            (center_x, ymin, center_z),
            (0.0, -1.0, 0.0),
            _bbox(xmin, ymin, zmin, xmax, ymin, zmax),
            [e(1), e(5), e(9), e(10)],
        ),
        _plane(
            f(4),
            dy * dz,
            (xmax, center_y, center_z),
            (1.0, 0.0, 0.0),
            _bbox(xmax, ymin, zmin, xmax, ymax, zmax),
            [e(2), e(6), e(10), e(11)],
        ),
        _plane(
            f(5),
            dx * dz,
            (center_x, ymax, center_z),
            (0.0, 1.0, 0.0),
            _bbox(xmin, ymax, zmin, xmax, ymax, zmax),
            [e(3), e(7), e(11), e(8)],
        ),
    ]
    edges = [
        _line(e(0), (xmin, ymin, zmin), (xmax, ymin, zmin), [f(0), f(2)]),
        _line(e(1), (xmax, ymin, zmin), (xmax, ymax, zmin), [f(0), f(3)]),
        _line(e(2), (xmax, ymax, zmin), (xmin, ymax, zmin), [f(0), f(4)]),
        _line(e(3), (xmin, ymax, zmin), (xmin, ymin, zmin), [f(0), f(5)]),
        _line(e(4), (xmin, ymin, zmax), (xmax, ymin, zmax), [f(1), f(2)]),
        _line(e(5), (xmax, ymin, zmax), (xmax, ymax, zmax), [f(1), f(3)]),
        _line(e(6), (xmax, ymax, zmax), (xmin, ymax, zmax), [f(1), f(4)]),
        _line(e(7), (xmin, ymax, zmax), (xmin, ymin, zmax), [f(1), f(5)]),
        _line(e(8), (xmin, ymin, zmin), (xmin, ymin, zmax), [f(2), f(5)]),
        _line(e(9), (xmax, ymin, zmin), (xmax, ymin, zmax), [f(2), f(3)]),
        _line(e(10), (xmax, ymax, zmin), (xmax, ymax, zmax), [f(4), f(3)]),
        _line(e(11), (xmin, ymax, zmin), (xmin, ymax, zmax), [f(4), f(5)]),
    ]
    return faces, edges


def _board_geometry(
    body_id: str,
    component_id: str,
    params: SyntheticParams,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, tuple[str, str]]]:
    faces, edges = _box_geometry(
        body_id,
        component_id,
        0.0,
        0.0,
        0.0,
        params.board_length,
        params.board_width,
        params.board_thickness,
    )
    holes: list[tuple[float, float, float]] = [
        (hole.x, hole.y, hole.diameter) for hole in params.mounting_holes
    ] + [(via.x, via.y, via.diameter) for via in params.vias]
    removed_area = sum(math.pi * diameter * diameter / 4.0 for _, _, diameter in holes)
    retained_area = params.board_length * params.board_width - removed_area
    centroid_x = (
        params.board_length * params.board_width * params.board_length / 2.0
        - sum(math.pi * diameter * diameter / 4.0 * x for x, _, diameter in holes)
    ) / retained_area
    centroid_y = (
        params.board_length * params.board_width * params.board_width / 2.0
        - sum(math.pi * diameter * diameter / 4.0 * y for _, y, diameter in holes)
    ) / retained_area
    faces[0]["area"] = retained_area
    faces[0]["centroid"] = (centroid_x, centroid_y, 0.0)
    faces[1]["area"] = retained_area
    faces[1]["centroid"] = (centroid_x, centroid_y, params.board_thickness)
    references: dict[str, tuple[str, str]] = {}
    for index, (x, y, diameter) in enumerate(holes):
        radius = diameter / 2.0
        face_id = f"{body_id}.f{6 + index}"
        bottom_edge_id = f"{body_id}.e{12 + 2 * index}"
        top_edge_id = f"{body_id}.e{13 + 2 * index}"
        faces[0]["edge_ids"].append(bottom_edge_id)
        faces[1]["edge_ids"].append(top_edge_id)
        faces.append(
            {
                **_cylinder_face(
                    face_id,
                    x,
                    y,
                    0.0,
                    params.board_thickness,
                    radius,
                    False,
                    [bottom_edge_id, top_edge_id],
                ),
            }
        )
        edges.append(_circle(bottom_edge_id, (x, y, 0.0), radius, [faces[0]["id"], face_id]))
        edges.append(
            _circle(top_edge_id, (x, y, params.board_thickness), radius, [faces[1]["id"], face_id])
        )
        key = "mounting_hole" if index < len(params.mounting_holes) else "via"
        local_index = index if key == "mounting_hole" else index - len(params.mounting_holes)
        references[f"{key}:{local_index}:face"] = (component_id, face_id)
        references[f"{key}:{local_index}:bottom_edge"] = (component_id, bottom_edge_id)
        references[f"{key}:{local_index}:top_edge"] = (component_id, top_edge_id)
    return faces, edges, references


def _pin_geometry(
    body_id: str,
    x: float,
    y: float,
    zmin: float,
    length: float,
    radius: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    face_id = f"{body_id}.f0"
    edge_id = f"{body_id}.e0"
    return [_cylinder_face(face_id, x, y, zmin, zmin + length, radius, True, [edge_id])], [
        _circle(edge_id, (x, y, zmin + length), radius, [face_id])
    ]


def _source_model(name: str) -> dict[str, Any]:
    return {
        "path": f"synthetic/pcba/{name}/model.prt",
        "units": "mm",
        "nx_version": None,
        "extracted_at": EXTRACTED_AT,
        "synthetic": True,
        "attributes": {},
    }


def _source_drawing(name: str, model_path: str) -> dict[str, Any]:
    return {
        "path": f"synthetic/pcba/{name}/drawing.prt",
        "nx_version": None,
        "extracted_at": EXTRACTED_AT,
        "synthetic": True,
        "model_part": model_path,
        "attributes": {},
    }


def build_model(params: SyntheticParams) -> tuple[RawModel, dict[str, _Entity]]:
    """Build and validate one raw model and return an entity lookup."""

    _validate_params(params)
    components: list[dict[str, Any]] = [
        {
            "id": "c0",
            "parent_id": None,
            "name": params.name,
            "part_name": params.name,
            "attributes": {},
            "transform": IDENTITY_4,
            "suppressed": False,
        }
    ]
    bodies: list[dict[str, Any]] = []
    entities: dict[str, _Entity] = {}
    component_specs: list[tuple[str, str, str, Any]] = [
        ("PCB1", "board", "c1", params),
        *[(c.refdes, "box", "", c) for c in params.box_components],
        *[(c.refdes, "connector", "", c) for c in params.connectors],
    ]
    component_specs[1:] = sorted(component_specs[1:], key=lambda item: item[0])
    component_id_by_ref: dict[str, str] = {"PCB1": "c1"}
    for index, (refdes, _kind, _, _spec) in enumerate(component_specs[1:], start=2):
        component_id_by_ref[refdes] = f"c{index}"
    for refdes, kind, fixed_id, spec in component_specs:
        component_id = fixed_id or component_id_by_ref[refdes]
        components.append(
            {
                "id": component_id,
                "parent_id": "c0",
                "name": refdes,
                "part_name": "PCB1" if refdes == "PCB1" else f"{refdes}_part",
                "attributes": {"REFDES": refdes},
                "transform": IDENTITY_4,
                "suppressed": False,
            }
        )
        if kind == "board":
            assert isinstance(spec, SyntheticParams)
            faces, edges, refs = _board_geometry(f"{component_id}.b0", component_id, spec)
            body: dict[str, Any] = {
                "id": f"{component_id}.b0",
                "component_id": component_id,
                "kind": "solid",
                "bbox": _bbox(
                    0.0, 0.0, 0.0, spec.board_length, spec.board_width, spec.board_thickness
                ),
                "volume": (
                    spec.board_length * spec.board_width * spec.board_thickness
                    - sum(
                        math.pi * hole.diameter**2 / 4.0 * spec.board_thickness
                        for hole in spec.mounting_holes
                    )
                    - sum(
                        math.pi * via.diameter**2 / 4.0 * spec.board_thickness for via in spec.vias
                    )
                ),
                "faces": faces,
                "edges": edges,
            }
            bodies.append(body)
            for face in faces:
                entities[face["id"]] = _Entity(refdes, face)
            for edge in edges:
                entities[edge["id"]] = _Entity(refdes, edge)
            for ref_key, (ref_component, entity_id) in refs.items():
                del ref_component
                entities[f"ref:{ref_key}"] = _Entity(
                    refdes, next(e for e in [*faces, *edges] if e["id"] == entity_id)
                )
            continue
        if kind == "box":
            assert isinstance(spec, BoxComponent)
            zmin = -spec.height if spec.side == "bottom" else params.board_thickness
            zmax = 0.0 if spec.side == "bottom" else params.board_thickness + spec.height
            faces, edges = _box_geometry(
                f"{component_id}.b0",
                component_id,
                spec.x,
                spec.y,
                zmin,
                spec.x + spec.size_x,
                spec.y + spec.size_y,
                zmax,
            )
            body = {
                "id": f"{component_id}.b0",
                "component_id": component_id,
                "kind": "solid",
                "bbox": _bbox(
                    spec.x, spec.y, zmin, spec.x + spec.size_x, spec.y + spec.size_y, zmax
                ),
                "volume": spec.size_x * spec.size_y * spec.height,
                "faces": faces,
                "edges": edges,
            }
            bodies.append(body)
            for face in faces:
                entities[face["id"]] = _Entity(refdes, face)
            for edge in edges:
                entities[edge["id"]] = _Entity(refdes, edge)
            continue
        assert isinstance(spec, Connector)
        zmin = params.board_thickness
        zmax = params.board_thickness + spec.height
        faces, edges = _box_geometry(
            f"{component_id}.b0",
            component_id,
            spec.x,
            spec.y,
            zmin,
            spec.x + spec.size_x,
            spec.y + spec.size_y,
            zmax,
        )
        body = {
            "id": f"{component_id}.b0",
            "component_id": component_id,
            "kind": "solid",
            "bbox": _bbox(spec.x, spec.y, zmin, spec.x + spec.size_x, spec.y + spec.size_y, zmax),
            "volume": spec.size_x * spec.size_y * spec.height,
            "faces": faces,
            "edges": edges,
        }
        bodies.append(body)
        for face in faces:
            entities[face["id"]] = _Entity(refdes, face)
        for edge in edges:
            entities[edge["id"]] = _Entity(refdes, edge)
        for row in range(spec.pin_rows):
            for col in range(spec.pin_cols):
                pin_number = row * spec.pin_cols + col + 1
                pin_body_id = f"{component_id}.b{pin_number}"
                pin_x, pin_y = _pin_position(spec, col, row)
                pin_faces, pin_edges = _pin_geometry(
                    pin_body_id,
                    pin_x,
                    pin_y,
                    zmax,
                    spec.pin_length_above_body,
                    spec.pin_diameter / 2.0,
                )
                pin_body = {
                    "id": pin_body_id,
                    "component_id": component_id,
                    "kind": "solid",
                    "bbox": _bbox(
                        pin_x - spec.pin_diameter / 2.0,
                        pin_y - spec.pin_diameter / 2.0,
                        zmax,
                        pin_x + spec.pin_diameter / 2.0,
                        pin_y + spec.pin_diameter / 2.0,
                        zmax + spec.pin_length_above_body,
                    ),
                    "volume": math.pi * (spec.pin_diameter / 2.0) ** 2 * spec.pin_length_above_body,
                    "faces": pin_faces,
                    "edges": pin_edges,
                }
                bodies.append(pin_body)
                for face in pin_faces:
                    entities[face["id"]] = _Entity(refdes, face)
                for edge in pin_edges:
                    entities[edge["id"]] = _Entity(refdes, edge)
    components.sort(key=lambda component: _id_key(component["id"]))
    bodies.sort(key=lambda body: _id_key(body["id"]))
    for body in bodies:
        body["faces"].sort(key=lambda face: _id_key(face["id"]))
        body["edges"].sort(key=lambda edge: _id_key(edge["id"]))
        for face in body["faces"]:
            face["edge_ids"] = sorted(face["edge_ids"], key=_id_key)
        for edge in body["edges"]:
            edge["face_ids"] = sorted(edge["face_ids"], key=_id_key)
    model = RawModel.model_validate(
        {
            "schema": "raw_model/0",
            "source": _source_model(params.name),
            "components": components,
            "bodies": bodies,
        }
    )
    return model, entities


def _entity_attachment(
    index: int,
    entity: _Entity,
    point_kind: str,
    view_id: str,
) -> dict[str, Any]:
    raw = entity.entity
    if raw["id"].split(".")[-1].startswith("f"):
        fingerprint = from_face(raw, entity.component_name)
    else:
        fingerprint = from_edge(raw, entity.component_name)
    point = raw.get("centroid") or raw.get("center")
    if point is None and raw.get("start") is not None and raw.get("end") is not None:
        point = tuple((raw["start"][axis] + raw["end"][axis]) / 2.0 for axis in range(3))
    return {
        "index": index,
        "entity_kind": "face" if raw["id"].split(".")[-1].startswith("f") else "edge",
        "fingerprint": fingerprint,
        "point": point,
        "point_kind": point_kind,
        "view_id": view_id,
        "trace_note": None,
    }


def _text_bbox(origin: tuple[float, float], text: str) -> tuple[float, float, float, float]:
    width = max(8.0, 2.5 * len(text))
    return (origin[0] - width / 2.0, origin[1] - 2.5, origin[0] + width / 2.0, origin[1] + 2.5)


def _format_mm(value: float) -> str:
    return f"{value:.2f}"


def _dimension(
    dimension_id: str,
    view_id: str,
    kind: str,
    direction: str | None,
    value: float,
    origin: tuple[float, float],
    attachments: list[dict[str, Any]],
    appended_text: dict[str, str] | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    formatted = text if text is not None else _format_mm(value)
    before = appended_text["before"] if appended_text is not None else ""
    after = appended_text["after"] if appended_text is not None else ""
    return {
        "id": dimension_id,
        "view_id": view_id,
        "kind": kind,
        "direction": direction,
        "value": value,
        "text": formatted,
        "text_overridden": False,
        "appended_text": appended_text,
        "tolerance": None,
        "origin": origin,
        "bbox": _text_bbox(origin, f"{before}{formatted}{after}"),
        "retained": False,
        "attachments": attachments,
    }


def _find_entity(entities: Mapping[str, _Entity], entity_id: str) -> _Entity:
    return entities[entity_id]


def _component_id(model: RawModel, name: str) -> str:
    return next(component.id for component in model.components if component.name == name)


def _face(entities: Mapping[str, _Entity], body_id: str, face_number: int) -> _Entity:
    return _find_entity(entities, f"{body_id}.f{face_number}")


def _hole_face(entities: Mapping[str, _Entity], index: int) -> _Entity:
    return entities[f"ref:mounting_hole:{index}:face"]


def _pin_face(entities: Mapping[str, _Entity], component_id: str, pin_number: int) -> _Entity:
    return _find_entity(entities, f"{component_id}.b{pin_number}.f0")


def build_drawing(
    params: SyntheticParams, model: RawModel, entities: Mapping[str, _Entity]
) -> RawDrawing:
    """Build a validated reference drawing attached to the generated model."""

    board_id = next(component.id for component in model.components if component.name == "PCB1")
    board_body_id = f"{board_id}.b0"
    top_view = RawView(
        id="v_top",
        name="TOP",
        kind="base",
        parent_id=None,
        model_view="Top",
        rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
        scale=1.0,
        center=(60.0, 180.0),
        bbox=(20.0, 150.0, 100.0, 210.0),
        representation="exact",
        out_of_date=False,
    )
    bottom_view = RawView(
        id="v_bottom",
        name="BOTTOM",
        kind="projected",
        parent_id="v_top",
        model_view="Bottom",
        rotation=(1.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, -1.0),
        scale=1.0,
        center=(220.0, 180.0),
        bbox=(180.0, 150.0, 260.0, 210.0),
        representation="exact",
        out_of_date=False,
    )
    max_top = max(
        [params.board_thickness]
        + [
            params.board_thickness + component.height
            for component in params.box_components
            if component.side == "top"
        ]
        + [
            params.board_thickness + connector.height + connector.pin_length_above_body
            for connector in params.connectors
        ]
    )
    min_bottom = min(
        [0.0]
        + [-component.height for component in params.box_components if component.side == "bottom"]
    )
    side_view = RawView(
        id="v_side",
        name="SIDE",
        kind="projected",
        parent_id="v_top",
        model_view="Front",
        # Looks along +Y from -Y: view x = model x, view y = model z (up).
        rotation=(1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -1.0, 0.0),
        scale=1.0,
        center=(60.0, 55.0 + (min_bottom + max_top) / 2.0),
        bbox=(20.0, 55.0 + min_bottom, 100.0, 55.0 + max_top),
        representation="exact",
        out_of_date=False,
    )

    datum = _hole_face(entities, 0)
    dimensions: list[dict[str, Any]] = []
    dimensions.append(
        _dimension(
            "d00_board_length",
            "v_top",
            "linear",
            "horizontal",
            params.board_length,
            (60.0, 140.0),
            [
                _entity_attachment(
                    0, _find_entity(entities, f"{board_body_id}.e1"), "mid", "v_top"
                ),
                _entity_attachment(
                    1, _find_entity(entities, f"{board_body_id}.e3"), "mid", "v_top"
                ),
            ],
        )
    )
    dimensions.append(
        _dimension(
            "d01_board_width",
            "v_top",
            "linear",
            "vertical",
            params.board_width,
            (110.0, 180.0),
            [
                _entity_attachment(
                    0, _find_entity(entities, f"{board_body_id}.e0"), "mid", "v_top"
                ),
                _entity_attachment(
                    1, _find_entity(entities, f"{board_body_id}.e2"), "mid", "v_top"
                ),
            ],
        )
    )
    dimensions.append(
        _dimension(
            "d02_board_thickness",
            "v_side",
            "linear",
            "vertical",
            params.board_thickness,
            (110.0, 55.0),
            [
                _entity_attachment(0, _face(entities, board_body_id, 1), "center", "v_side"),
                _entity_attachment(1, _face(entities, board_body_id, 0), "center", "v_side"),
            ],
        )
    )

    dimension_number = 3
    for index, hole in enumerate(params.mounting_holes[1:], start=1):
        delta_x = hole.x - params.mounting_holes[0].x
        delta_y = hole.y - params.mounting_holes[0].y
        target = _hole_face(entities, index)
        dimensions.append(
            _dimension(
                f"d{dimension_number:02d}_hole_{index}_x",
                "v_top",
                "ordinate",
                "horizontal",
                delta_x,
                (130.0, 130.0 - 8.0 * index),
                [
                    _entity_attachment(0, datum, "center", "v_top"),
                    _entity_attachment(1, target, "center", "v_top"),
                ],
            )
        )
        dimension_number += 1
        dimensions.append(
            _dimension(
                f"d{dimension_number:02d}_hole_{index}_y",
                "v_top",
                "ordinate",
                "vertical",
                delta_y,
                (145.0 + 8.0 * index, 130.0),
                [
                    _entity_attachment(0, datum, "center", "v_top"),
                    _entity_attachment(1, target, "center", "v_top"),
                ],
            )
        )
        dimension_number += 1
    diameter_groups: dict[float, list[int]] = {}
    for index, hole in enumerate(params.mounting_holes):
        diameter_groups.setdefault(hole.diameter, []).append(index)
    for diameter, indices in sorted(diameter_groups.items()):
        text = f"⌀{_format_mm(diameter)}"
        appended = (
            {"before": f"{len(indices)}X", "after": "", "above": "", "below": ""}
            if len(indices) > 1
            else None
        )
        dimensions.append(
            _dimension(
                f"d{dimension_number:02d}_hole_diameter_{_format_mm(diameter).replace('.', '_')}",
                "v_top",
                "diameter",
                None,
                diameter,
                (300.0, 235.0 - 8.0 * len(indices)),
                [_entity_attachment(0, _hole_face(entities, indices[0]), "center", "v_top")],
                appended_text=appended,
                text=text,
            )
        )
        dimension_number += 1

    for connector_index, connector in enumerate(params.connectors):
        connector_component_id = next(
            component.id for component in model.components if component.name == connector.refdes
        )
        pin1_x, pin1_y = _pin_position(connector, 0, 0)
        delta_x = pin1_x - params.mounting_holes[0].x
        delta_y = pin1_y - params.mounting_holes[0].y
        pin1 = _pin_face(entities, connector_component_id, 1)
        dimensions.append(
            _dimension(
                f"d{dimension_number:02d}_{connector.refdes}_x",
                "v_top",
                "linear",
                "horizontal",
                delta_x,
                (270.0, 115.0 - connector_index * 12.0),
                [
                    _entity_attachment(0, datum, "center", "v_top"),
                    _entity_attachment(1, pin1, "center", "v_top"),
                ],
            )
        )
        dimension_number += 1
        dimensions.append(
            _dimension(
                f"d{dimension_number:02d}_{connector.refdes}_y",
                "v_top",
                "linear",
                "vertical",
                delta_y,
                (300.0, 115.0 - connector_index * 12.0),
                [
                    _entity_attachment(0, datum, "center", "v_top"),
                    _entity_attachment(1, pin1, "center", "v_top"),
                ],
            )
        )
        dimension_number += 1
        if connector.pin_cols > 1:
            pin2 = _pin_face(entities, connector_component_id, 2)
            appended = (
                {
                    "before": f"{connector.pin_cols - 1}X",
                    "after": "",
                    "above": "",
                    "below": "",
                }
                if connector.pin_cols - 1 > 1
                else None
            )
            dimensions.append(
                _dimension(
                    f"d{dimension_number:02d}_{connector.refdes}_pitch",
                    "v_top",
                    "linear",
                    "horizontal",
                    connector.pitch,
                    (270.0, 90.0 - connector_index * 12.0),
                    [
                        _entity_attachment(0, pin1, "center", "v_top"),
                        _entity_attachment(1, pin2, "center", "v_top"),
                    ],
                    appended_text=appended,
                )
            )
            dimension_number += 1

    top_candidates: list[_Entity] = [
        _face(
            entities,
            f"{_component_id(model, box.refdes)}.b0",
            1,
        )
        for box in params.box_components
        if box.side == "top"
    ]
    for connector in params.connectors:
        connector_id = next(
            component.id for component in model.components if component.name == connector.refdes
        )
        top_candidates.append(_face(entities, f"{connector_id}.b0", 1))
        top_candidates.extend(
            _find_entity(entities, f"{connector_id}.b{pin_number}.f0")
            for pin_number in range(1, connector.pin_rows * connector.pin_cols + 1)
        )
    top_face = max(
        top_candidates or [_face(entities, board_body_id, 1)],
        key=lambda entity: entity.entity["bbox"][5],
    )
    bottom_components = [
        component for component in params.box_components if component.side == "bottom"
    ]
    if bottom_components:
        lowest = max(bottom_components, key=lambda component: component.height)
        lowest_id = next(
            component.id for component in model.components if component.name == lowest.refdes
        )
        bottom_face = _face(entities, f"{lowest_id}.b0", 0)
    else:
        bottom_face = _face(entities, board_body_id, 0)
    above = top_face.entity["bbox"][5] - params.board_thickness
    below = -bottom_face.entity["bbox"][2]
    dimensions.append(
        _dimension(
            f"d{dimension_number:02d}_height_above",
            "v_side",
            "linear",
            "vertical",
            above,
            (150.0, 72.0),
            [
                _entity_attachment(0, _face(entities, board_body_id, 1), "center", "v_side"),
                _entity_attachment(1, top_face, "center", "v_side"),
            ],
        )
    )
    dimension_number += 1
    dimensions.append(
        _dimension(
            f"d{dimension_number:02d}_height_below",
            "v_side",
            "linear",
            "vertical",
            below,
            (180.0, 42.0),
            [
                _entity_attachment(0, _face(entities, board_body_id, 0), "center", "v_side"),
                _entity_attachment(1, bottom_face, "center", "v_side"),
            ],
        )
    )

    drawing = RawDrawing.model_validate(
        {
            "schema": "raw_drawing/0",
            "source": _source_drawing(params.name, _source_model(params.name)["path"]),
            "sheets": [
                RawSheet(
                    id="s0",
                    name="A3",
                    width=420.0,
                    height=297.0,
                    scale=1.0,
                    projection="first",
                    standard="ISO",
                    views=sorted(
                        [top_view, bottom_view, side_view], key=lambda view: _id_key(view.id)
                    ),
                    dimensions=sorted(
                        [RawDimension.model_validate(dimension) for dimension in dimensions],
                        key=lambda dimension: _id_key(dimension.id),
                    ),
                    notes=[
                        {
                            "id": "n0",
                            "text": "NOTES: SYNTHETIC FIXTURE",
                            "origin": (300.0, 30.0),
                            "view_id": None,
                            "has_leader": False,
                        }
                    ],
                    tables=[
                        {
                            "id": "t0",
                            "kind": "title_block",
                            "origin": (320.0, 255.0),
                            "rows": [["TITLE", params.name], ["SCALE", "1:1"]],
                        }
                    ],
                )
            ],
        }
    )
    return drawing


def _params_payload(params: SyntheticParams) -> dict[str, Any]:
    payload = asdict(params)
    payload["synthetic"] = True
    return payload


def _write_fixture(root: Path, params: SyntheticParams, include_drawing: bool) -> None:
    model, entities = build_model(params)
    target = root / params.name
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / "params.json", _params_payload(params))
    write_json(target / "raw_model.json", model.model_dump(by_alias=True))
    if include_drawing:
        drawing = build_drawing(params, model, entities)
        write_json(target / "raw_drawing.json", drawing.model_dump(by_alias=True))


def default_params() -> SyntheticParams:
    """Return the reference PCBA parameters."""

    return SyntheticParams(
        name="reference",
        board_length=80.0,
        board_width=60.0,
        board_thickness=1.6,
        mounting_holes=(
            MountingHole(8.0, 8.0, 3.2),
            MountingHole(72.0, 8.0, 3.2),
            MountingHole(72.0, 52.0, 3.2),
            MountingHole(8.0, 52.0, 3.2),
        ),
        vias=(
            Via(20.0, 20.0, 0.4),
            Via(40.0, 20.0, 0.4),
            Via(60.0, 20.0, 0.4),
            Via(20.0, 40.0, 0.4),
            Via(40.0, 40.0, 0.4),
            Via(60.0, 40.0, 0.4),
        ),
        box_components=(
            BoxComponent("C1", "top", 10.0, 20.0, 5.0, 5.0, 2.5),
            BoxComponent("C2", "top", 17.0, 20.0, 5.0, 5.0, 2.5),
            BoxComponent("D1", "bottom", 45.0, 45.0, 8.0, 5.0, 3.2),
            BoxComponent("L1", "top", 10.0, 30.0, 7.0, 5.0, 4.0),
            BoxComponent("R1", "top", 10.0, 10.0, 5.0, 5.0, 2.0),
            BoxComponent("R2", "top", 17.0, 10.0, 5.0, 5.0, 2.0),
            BoxComponent("U1", "top", 27.0, 28.0, 14.0, 12.0, 14.0),
            BoxComponent("C3", "bottom", 57.0, 45.0, 5.0, 5.0, 2.4),
        ),
        connectors=(Connector("J1", 48.0, 12.0, 16.0, 14.0, 6.0, 2, 5, 2.54, 0.8, 3.0),),
    )


def sibling_params() -> tuple[SyntheticParams, ...]:
    """Return the three model-only siblings of the reference fixture."""

    reference = default_params()
    return (
        replace(
            reference,
            name="sibling_board_size",
            board_length=90.0,
            board_width=65.0,
        ),
        replace(
            reference,
            name="sibling_moved_holes",
            mounting_holes=(
                MountingHole(10.0, 10.0, 3.2),
                MountingHole(70.0, 10.0, 3.2),
                MountingHole(70.0, 50.0, 3.2),
                MountingHole(10.0, 50.0, 3.2),
            ),
        ),
        replace(
            reference,
            name="sibling_extra_connector",
            connectors=(
                *reference.connectors,
                Connector("J2", 12.0, 42.0, 14.0, 10.0, 4.0, 2, 4, 2.54, 0.8, 2.5),
            ),
        ),
    )


def all_params() -> tuple[SyntheticParams, ...]:
    return (default_params(), *sibling_params())


def generate_all(root: Path = FIXTURE_ROOT) -> None:
    """Write the reference, siblings, and their parameter files under ``root``."""

    root.mkdir(parents=True, exist_ok=True)
    _write_fixture(root, default_params(), include_drawing=True)
    for params in sibling_params():
        _write_fixture(root, params, include_drawing=False)


def _check() -> int:
    with tempfile.TemporaryDirectory(prefix=".synthetic-check-", dir=ROOT) as temporary:
        generated = Path(temporary) / "pcba"
        generate_all(generated)
        expected_files = sorted(path.relative_to(generated) for path in generated.rglob("*.json"))
        committed_files = sorted(
            path.relative_to(FIXTURE_ROOT) for path in FIXTURE_ROOT.rglob("*.json")
        )
        problems: list[str] = []
        for relative in sorted(set(expected_files) | set(committed_files)):
            expected = generated / relative
            committed = FIXTURE_ROOT / relative
            if (
                not expected.is_file()
                or not committed.is_file()
                or expected.read_bytes() != committed.read_bytes()
            ):
                problems.append(str(relative))
        for problem in problems:
            print(f"different: fixtures/synthetic/{problem}", file=sys.stderr)
        return 1 if problems else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when committed JSON differs")
    args = parser.parse_args(argv)
    if args.check:
        return _check()
    generate_all()
    print(f"wrote synthetic PCBA fixtures to {FIXTURE_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
