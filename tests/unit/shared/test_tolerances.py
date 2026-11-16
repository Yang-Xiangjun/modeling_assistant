"""Tests for shared tolerance configuration."""

from dataclasses import FrozenInstanceError

import pytest
from drawgen_shared.tolerances import DEFAULT, Tolerances


def test_default_values_and_dict() -> None:
    expected = {
        "linear_mm": 0.001,
        "angular_deg": 0.01,
        "fingerprint_size_rel": 1e-6,
        "fingerprint_size_abs": 1e-4,
        "fingerprint_centroid_mm": 0.001,
        "fingerprint_direction_rad": 1e-4,
        "fingerprint_radius_mm": 0.001,
    }
    assert Tolerances(**expected) == DEFAULT
    assert DEFAULT.to_dict() == expected


def test_tolerances_are_frozen() -> None:
    with pytest.raises(FrozenInstanceError):
        DEFAULT.linear_mm = 1.0  # type: ignore[misc]
