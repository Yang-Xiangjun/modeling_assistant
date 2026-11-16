"""Tests for the standard-library vector helpers."""

from math import pi, sqrt

import pytest
from drawgen_shared.vec import (
    add,
    angle_between,
    as_vec3,
    bbox_of_points,
    bbox_union,
    cross,
    distance,
    dot,
    is_parallel,
    midpoint,
    norm,
    normalize,
    scale,
    sub,
)


def test_vector_arithmetic_and_measurements() -> None:
    a = (1.0, 2.0, 3.0)
    b = (-2.0, 4.0, 1.0)
    assert add(a, b) == (-1.0, 6.0, 4.0)
    assert sub(a, b) == (3.0, -2.0, 2.0)
    assert scale(a, 2.0) == (2.0, 4.0, 6.0)
    assert dot(a, b) == 9.0
    assert cross(a, b) == (-10.0, -7.0, 8.0)
    assert norm(a) == sqrt(14.0)
    assert normalize((0.0, 0.0, 2.0)) == (0.0, 0.0, 1.0)
    assert distance(a, b) == sqrt(17.0)
    assert midpoint(a, b) == (-0.5, 3.0, 2.0)


def test_angles_and_parallel_sign_handling() -> None:
    assert angle_between((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)) == pytest.approx(pi / 2.0)
    assert is_parallel((1.0, 0.0, 0.0), (-2.0, 0.0, 0.0), 0.0)
    assert not is_parallel((1.0, 0.0, 0.0), (-2.0, 0.0, 0.0), 0.0, ignore_sign=False)
    assert is_parallel((1.0, 0.0, 0.0), (1.0, 1e-5, 0.0), 1e-4)
    with pytest.raises(ValueError):
        is_parallel((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), -1.0)


def test_zero_vectors_raise() -> None:
    with pytest.raises(ValueError):
        normalize((0.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        angle_between((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))


def test_bounding_boxes_and_conversion() -> None:
    points = [(1.0, 2.0, 3.0), (-1.0, 5.0, 0.0), (2.0, -2.0, 4.0)]
    first = bbox_of_points(points)
    second = (-3.0, 0.0, 2.0, 0.0, 8.0, 5.0)
    assert first == (-1.0, -2.0, 0.0, 2.0, 5.0, 4.0)
    assert bbox_union([first, second]) == (-3.0, -2.0, 0.0, 2.0, 8.0, 5.0)
    assert bbox_union(first, second) == (-3.0, -2.0, 0.0, 2.0, 8.0, 5.0)
    assert as_vec3([1, 2.5, 3]) == (1.0, 2.5, 3.0)
    with pytest.raises(ValueError):
        bbox_of_points([])
    with pytest.raises(ValueError):
        bbox_union([])


@pytest.mark.parametrize("bad", [[1.0, 2.0], [1.0, 2.0, 3.0, 4.0], [1.0, float("nan"), 3.0]])
def test_as_vec3_rejects_invalid_values(bad: list[float]) -> None:
    with pytest.raises(ValueError):
        as_vec3(bad)
