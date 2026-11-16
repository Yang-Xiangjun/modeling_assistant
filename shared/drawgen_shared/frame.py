"""Orthonormal coordinate frames and conversions between frame coordinates."""

from __future__ import annotations

from dataclasses import dataclass

from .vec import Vec3, add, cross, dot, normalize, scale, sub


@dataclass(frozen=True)
class Frame:
    """A right-handed orthonormal frame expressed in model coordinates."""

    origin: Vec3
    x: Vec3
    y: Vec3
    z: Vec3

    @classmethod
    def from_axes(cls, origin: Vec3, x: Vec3, z: Vec3) -> Frame:
        """Build an orthonormal right-handed frame from approximate X and Z axes."""

        z_axis = normalize(z)
        y_axis = normalize(cross(z_axis, x))
        # Re-orthogonalise X after constructing Y, which also removes any small
        # component of the supplied X axis along Z.
        x_axis = normalize(cross(y_axis, z_axis))
        y_axis = normalize(cross(z_axis, x_axis))
        return cls(origin=origin, x=x_axis, y=y_axis, z=z_axis)

    def to_local(self, point: Vec3) -> Vec3:
        """Convert a model-space point to this frame's coordinates."""

        relative = sub(point, self.origin)
        return (dot(relative, self.x), dot(relative, self.y), dot(relative, self.z))

    def to_global(self, point: Vec3) -> Vec3:
        """Convert a point in this frame to model-space coordinates."""

        return add(
            self.origin,
            add(scale(self.x, point[0]), add(scale(self.y, point[1]), scale(self.z, point[2]))),
        )

    def dir_to_local(self, direction: Vec3) -> Vec3:
        """Convert a model-space direction to this frame without translation."""

        return (dot(direction, self.x), dot(direction, self.y), dot(direction, self.z))

    def dir_to_global(self, direction: Vec3) -> Vec3:
        """Convert a frame-space direction to model coordinates without translation."""

        return add(
            scale(self.x, direction[0]),
            add(scale(self.y, direction[1]), scale(self.z, direction[2])),
        )

    def rotation_rows(self) -> tuple[float, float, float, float, float, float, float, float, float]:
        """Return the row-major model-to-frame rotation matrix."""

        return (*self.x, *self.y, *self.z)


WORLD = Frame(
    origin=(0.0, 0.0, 0.0),
    x=(1.0, 0.0, 0.0),
    y=(0.0, 1.0, 0.0),
    z=(0.0, 0.0, 1.0),
)
"""The identity frame at the model world origin."""
