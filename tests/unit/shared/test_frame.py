"""Tests for coordinate frames."""

import pytest
from drawgen_shared.frame import WORLD, Frame
from drawgen_shared.vec import cross, dot, norm


def test_world_is_identity() -> None:
    point = (2.0, -3.0, 4.5)
    direction = (-1.0, 2.0, 0.5)
    assert WORLD.to_local(point) == point
    assert WORLD.to_global(point) == point
    assert WORLD.dir_to_local(direction) == direction
    assert WORLD.dir_to_global(direction) == direction
    assert WORLD.rotation_rows() == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def test_from_axes_round_trips_and_is_orthonormal() -> None:
    frame = Frame.from_axes((10.0, 20.0, 30.0), (1.0, 0.2, 0.1), (0.0, 0.1, 1.0))
    assert frame.to_global(frame.to_local((12.0, 18.0, 34.0))) == pytest.approx((12.0, 18.0, 34.0))
    direction = (0.2, -1.3, 4.0)
    assert frame.dir_to_global(frame.dir_to_local(direction)) == pytest.approx(direction)
    for axis in (frame.x, frame.y, frame.z):
        assert norm(axis) == pytest.approx(1.0)
    assert dot(frame.x, frame.y) == pytest.approx(0.0)
    assert dot(frame.x, frame.z) == pytest.approx(0.0)
    assert dot(frame.y, frame.z) == pytest.approx(0.0)
    assert cross(frame.x, frame.y) == pytest.approx(frame.z)
    assert frame.rotation_rows() == (*frame.x, *frame.y, *frame.z)


def test_from_axes_rejects_degenerate_axes() -> None:
    with pytest.raises(ValueError):
        Frame.from_axes((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        Frame.from_axes((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (1.0, 0.0, 0.0))
