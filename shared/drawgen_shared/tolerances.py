"""Shared geometric and fingerprint tolerance configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tolerances:
    """Numerical tolerances used across geometry extraction and matching."""

    linear_mm: float = 0.001
    angular_deg: float = 0.01
    fingerprint_size_rel: float = 1e-6
    fingerprint_size_abs: float = 1e-4
    fingerprint_centroid_mm: float = 0.001
    fingerprint_direction_rad: float = 1e-4
    fingerprint_radius_mm: float = 0.001

    def to_dict(self) -> dict[str, float]:
        """Return the tolerance values as a JSON-ready dictionary."""

        return {
            "linear_mm": self.linear_mm,
            "angular_deg": self.angular_deg,
            "fingerprint_size_rel": self.fingerprint_size_rel,
            "fingerprint_size_abs": self.fingerprint_size_abs,
            "fingerprint_centroid_mm": self.fingerprint_centroid_mm,
            "fingerprint_direction_rad": self.fingerprint_direction_rad,
            "fingerprint_radius_mm": self.fingerprint_radius_mm,
        }


DEFAULT = Tolerances()
"""The default tolerance configuration from HANDOFF.md section 8.1."""
