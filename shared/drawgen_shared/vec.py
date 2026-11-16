"""Small three-dimensional vector helpers used by the worker and core code."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import cast

Vec3 = tuple[float, float, float]
BBox3 = tuple[float, float, float, float, float, float]


def add(a: Vec3, b: Vec3) -> Vec3:
    """Return the component-wise sum of two vectors."""

    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec3, b: Vec3) -> Vec3:
    """Return the component-wise difference ``a - b``."""

    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(vector: Vec3, factor: float) -> Vec3:
    """Return ``vector`` multiplied by ``factor``."""

    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def dot(a: Vec3, b: Vec3) -> float:
    """Return the dot product of two vectors."""

    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    """Return the right-handed cross product ``a x b``."""

    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(vector: Vec3) -> float:
    """Return the Euclidean length of a vector."""

    return math.sqrt(dot(vector, vector))


def normalize(vector: Vec3) -> Vec3:
    """Return a unit vector, raising ``ValueError`` for a zero vector."""

    length = norm(vector)
    if length == 0.0:
        raise ValueError("cannot normalize a zero vector")
    return scale(vector, 1.0 / length)


def distance(a: Vec3, b: Vec3) -> float:
    """Return the Euclidean distance between two points."""

    return norm(sub(a, b))


def angle_between(a: Vec3, b: Vec3) -> float:
    """Return the smaller angle between two non-zero vectors in radians."""

    unit_a = normalize(a)
    unit_b = normalize(b)
    cosine = max(-1.0, min(1.0, dot(unit_a, unit_b)))
    return math.acos(cosine)


def is_parallel(a: Vec3, b: Vec3, tol_rad: float, ignore_sign: bool = True) -> bool:
    """Return whether two non-zero vectors are parallel within an angular tolerance."""

    if tol_rad < 0.0:
        raise ValueError("angular tolerance must be non-negative")
    angle = angle_between(a, b)
    if ignore_sign:
        angle = min(angle, math.pi - angle)
    return angle <= tol_rad


def midpoint(a: Vec3, b: Vec3) -> Vec3:
    """Return the midpoint between two points."""

    return scale(add(a, b), 0.5)


def bbox_of_points(points: Iterable[Vec3]) -> BBox3:
    """Return the axis-aligned bounding box of points, or raise for no points."""

    iterator = iter(points)
    try:
        first = next(iterator)
    except StopIteration as exc:
        raise ValueError("at least one point is required") from exc

    xmin = xmax = first[0]
    ymin = ymax = first[1]
    zmin = zmax = first[2]
    for point in iterator:
        xmin = min(xmin, point[0])
        ymin = min(ymin, point[1])
        zmin = min(zmin, point[2])
        xmax = max(xmax, point[0])
        ymax = max(ymax, point[1])
        zmax = max(zmax, point[2])
    return (xmin, ymin, zmin, xmax, ymax, zmax)


def bbox_union(
    boxes: Iterable[BBox3] | BBox3,
    *additional: BBox3,
) -> BBox3:
    """Return the union of bounding boxes.

    The usual form accepts an iterable of boxes.  Passing two or more boxes as
    positional arguments is also supported for convenient composition.
    """

    if additional:
        all_boxes = [cast(BBox3, boxes), *additional]
    elif (
        isinstance(boxes, (tuple, list))
        and len(boxes) == 6
        and all(isinstance(value, (int, float)) for value in boxes)
    ):
        all_boxes = [cast(BBox3, boxes)]
    else:
        all_boxes = list(cast(Iterable[BBox3], boxes))

    if not all_boxes:
        raise ValueError("at least one bounding box is required")

    first = all_boxes[0]
    xmin, ymin, zmin, xmax, ymax, zmax = first
    for box in all_boxes[1:]:
        xmin = min(xmin, box[0])
        ymin = min(ymin, box[1])
        zmin = min(zmin, box[2])
        xmax = max(xmax, box[3])
        ymax = max(ymax, box[4])
        zmax = max(zmax, box[5])
    return (xmin, ymin, zmin, xmax, ymax, zmax)


def as_vec3(seq: Sequence[float]) -> Vec3:
    """Convert a length-three sequence to finite floating-point coordinates."""

    if isinstance(seq, (str, bytes)):
        raise ValueError("a Vec3 must contain exactly three numeric values")
    try:
        if len(seq) != 3:
            raise ValueError("a Vec3 must contain exactly three values")
        values = (float(seq[0]), float(seq[1]), float(seq[2]))
    except (TypeError, ValueError) as exc:
        raise ValueError("Vec3 values must be finite floats") from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Vec3 values must be finite floats")
    return values
