"""The shared tolerance and fingerprint representations agree with contracts."""

from drawgen_shared.fingerprint import from_edge, from_face
from drawgen_shared.tolerances import DEFAULT

from drawgen.contracts.common import Fingerprint as ContractFingerprint
from drawgen.contracts.common import Tolerances as ContractTolerances


def test_tolerances_and_fingerprints_agree() -> None:
    assert ContractTolerances().model_dump() == DEFAULT.to_dict()
    face = from_face(
        {
            "geom": "plane",
            "area": 10.0,
            "centroid": [1.0, 2.0, 3.0],
            "direction": [0.0, 0.0, 1.0],
            "radius": None,
            "bbox": [0.0, 0.0, 3.0, 2.0, 4.0, 3.0],
        }
    )
    edge = from_edge(
        {
            "geom": "line",
            "length": 10.0,
            "start": [0.0, 0.0, 0.0],
            "end": [10.0, 0.0, 0.0],
            "center": None,
            "direction": [1.0, 0.0, 0.0],
            "radius": None,
        }
    )
    assert ContractFingerprint.model_validate(face)
    assert ContractFingerprint.model_validate(edge)
