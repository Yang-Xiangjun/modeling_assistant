"""Tests for fingerprint construction and tolerant matching."""

from math import cos, sin
from typing import Any, cast

import pytest
from drawgen_shared.fingerprint import Fingerprint, from_edge, from_face, is_same, match


def _face(**changes: Any) -> dict[str, Any]:
    face: dict[str, Any] = {
        "geom": "plane",
        "area": 10.0,
        "centroid": [1.0, 2.0, 3.0],
        "direction": [0.0, 0.0, 1.0],
        "radius": None,
        "bbox": [0.0, 0.0, 3.0, 2.0, 4.0, 3.0],
    }
    face.update(changes)
    return face


def _edge(**changes: Any) -> dict[str, Any]:
    edge: dict[str, Any] = {
        "geom": "line",
        "length": 10.0,
        "start": [0.0, 0.0, 0.0],
        "end": [10.0, 0.0, 0.0],
        "center": None,
        "direction": [1.0, 0.0, 0.0],
        "radius": None,
    }
    edge.update(changes)
    return edge


def test_from_face_is_json_ready() -> None:
    fingerprint = from_face(_face(), component_path="root/board")
    assert fingerprint == {
        "kind": "face",
        "geom": "plane",
        "size": 10.0,
        "centroid": [1.0, 2.0, 3.0],
        "direction": [0.0, 0.0, 1.0],
        "radius": None,
        "bbox": [0.0, 0.0, 3.0, 2.0, 4.0, 3.0],
        "component_path": "root/board",
    }


def test_from_edge_centroid_and_circle_bbox() -> None:
    line = from_edge(_edge())
    assert line["centroid"] == [5.0, 0.0, 0.0]
    assert line["bbox"] == [0.0, 0.0, 0.0, 10.0, 0.0, 0.0]
    circle = from_edge(
        _edge(
            geom="circle",
            length=2.0 * 3.141592653589793 * 2.0,
            start=None,
            end=None,
            center=[1.0, 2.0, 3.0],
            direction=[0.0, 0.0, 1.0],
            radius=2.0,
        )
    )
    assert circle["centroid"] == [1.0, 2.0, 3.0]
    assert circle["bbox"] == [pytest.approx(-1.0), pytest.approx(0.0), 3.0, 3.0, 4.0, 3.0]


def test_from_edge_requires_centroid_data() -> None:
    with pytest.raises(ValueError):
        from_edge(_edge(start=None, end=None, center=None))


def _candidate(base: Fingerprint, **changes: Any) -> Fingerprint:
    result: dict[str, Any] = dict(base)
    result.update(changes)
    return cast(Fingerprint, result)


def test_match_and_ambiguous_outcomes() -> None:
    base = from_face(_face())
    assert match(base, [_candidate(base, size=20.0)]).status == "no_match"
    one = match(base, [_candidate(base, component_path="one")])
    assert one.status == "match"
    assert one.index == 0
    assert one.indices == (0,)
    many = match(base, [base, _candidate(base, component_path="two")])
    assert many.status == "ambiguous"
    assert many.index is None
    assert many.indices == (0, 1)


def test_size_relative_tolerance_boundary() -> None:
    base = from_face(_face(area=1000.0))
    assert is_same(base, _candidate(base, size=1000.0 + 0.000999))
    assert not is_same(base, _candidate(base, size=1000.0 + 0.001001))


def test_size_absolute_tolerance_boundary() -> None:
    base = from_face(_face(area=0.0))
    assert is_same(base, _candidate(base, size=0.000099))
    assert not is_same(base, _candidate(base, size=0.000101))


def test_centroid_direction_and_radius_boundaries() -> None:
    base = from_face(_face(radius=1.0))
    assert is_same(base, _candidate(base, centroid=[1.000999, 2.0, 3.0]))
    assert not is_same(base, _candidate(base, centroid=[1.001001, 2.0, 3.0]))

    inside_angle = 0.000099
    outside_angle = 0.000101
    assert is_same(
        base,
        _candidate(base, direction=[sin(inside_angle), 0.0, cos(inside_angle)]),
    )
    assert not is_same(
        base,
        _candidate(base, direction=[sin(outside_angle), 0.0, cos(outside_angle)]),
    )
    assert is_same(base, _candidate(base, radius=1.000999))
    assert not is_same(base, _candidate(base, radius=1.001001))


def test_direction_sign_and_none_mismatches_and_identity_fields() -> None:
    base = from_face(_face(radius=1.0))
    assert is_same(base, _candidate(base, direction=[0.0, 0.0, -1.0]))
    assert not is_same(base, _candidate(base, direction=None))
    assert not is_same(base, _candidate(base, radius=None))
    assert not is_same(base, _candidate(base, kind="edge"))
    assert not is_same(base, _candidate(base, geom="cylinder"))
