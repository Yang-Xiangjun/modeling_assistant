"""Regression tests for the deterministic synthetic PCBA fixture pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from drawgen_shared.fingerprint import Fingerprint, from_edge, from_face, match
from jsonschema import validate

from drawgen.contracts.raw_drawing import RawDrawing
from drawgen.contracts.raw_model import RawModel
from tools import make_synthetic

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "synthetic" / "pcba"


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _model_entities(model: RawModel) -> tuple[dict[str, dict[str, Any]], list[Fingerprint]]:
    entities: dict[str, dict[str, Any]] = {}
    fingerprints: list[Fingerprint] = []
    component_names = {component.id: component.name for component in model.components}
    for body in model.bodies:
        for face in body.faces:
            raw = face.model_dump()
            entities[face.id] = raw
            fingerprints.append(from_face(raw, component_names[body.component_id]))
        for edge in body.edges:
            raw = edge.model_dump()
            entities[edge.id] = raw
            fingerprints.append(from_edge(raw, component_names[body.component_id]))
    return entities, fingerprints


def _point(entity: dict[str, Any]) -> list[float]:
    if entity.get("centroid") is not None:
        return cast(list[float], entity["centroid"])
    if entity.get("center") is not None:
        return cast(list[float], entity["center"])
    assert entity["start"] is not None and entity["end"] is not None
    return [(entity["start"][axis] + entity["end"][axis]) / 2.0 for axis in range(3)]


def test_every_committed_json_validates_against_contracts_and_schemas() -> None:
    model_schema = _json(REPO_ROOT / "schemas" / "raw_model.schema.json")
    drawing_schema = _json(REPO_ROOT / "schemas" / "raw_drawing.schema.json")
    for path in sorted(FIXTURE_ROOT.rglob("*.json")):
        payload = _json(path)
        if "synthetic" in payload:
            assert payload["synthetic"] is True
        if path.name == "raw_model.json":
            RawModel.model_validate(payload)
            validate(payload, model_schema)
        elif path.name == "raw_drawing.json":
            RawDrawing.model_validate(payload)
            validate(payload, drawing_schema)


def test_committed_fixtures_equal_regeneration(tmp_path: Path) -> None:
    generated = tmp_path / "pcba"
    make_synthetic.generate_all(generated)
    expected = sorted(path.relative_to(generated) for path in generated.rglob("*.json"))
    committed = sorted(path.relative_to(FIXTURE_ROOT) for path in FIXTURE_ROOT.rglob("*.json"))
    assert expected == committed
    for relative in expected:
        assert (generated / relative).read_bytes() == (FIXTURE_ROOT / relative).read_bytes()


def test_drawing_attachments_match_one_entity_and_dimension_values() -> None:
    model_payload = _json(FIXTURE_ROOT / "reference" / "raw_model.json")
    drawing = RawDrawing.model_validate(_json(FIXTURE_ROOT / "reference" / "raw_drawing.json"))
    model = RawModel.model_validate(model_payload)
    raw_entities, raw_fingerprints = _model_entities(model)
    candidates = list(raw_entities.items())
    for dimension in drawing.sheets[0].dimensions:
        attached: list[dict[str, Any]] = []
        for attachment in dimension.attachments:
            assert attachment.fingerprint is not None
            result = match(
                cast(Fingerprint, attachment.fingerprint.model_dump()),
                raw_fingerprints,
            )
            assert result.status == "match"
            assert result.index is not None
            entity_id = candidates[result.index][0]
            attached.append(raw_entities[entity_id])
        assert dimension.value is not None
        if dimension.kind == "diameter":
            assert attached[0]["radius"] is not None
            assert dimension.value == pytest.approx(2.0 * attached[0]["radius"], abs=1e-9)
        elif dimension.kind == "ordinate":
            axis = 0 if dimension.direction == "horizontal" else 1
            assert dimension.value == pytest.approx(
                attached[1]["centroid"][axis] - attached[0]["centroid"][axis], abs=1e-9
            )
        elif dimension.id.endswith("_x") or dimension.id.endswith("_pitch"):
            assert dimension.value == pytest.approx(
                _point(attached[1])[0] - _point(attached[0])[0], abs=1e-9
            )
        elif dimension.id.endswith("_y"):
            assert dimension.value == pytest.approx(
                _point(attached[1])[1] - _point(attached[0])[1], abs=1e-9
            )
        elif dimension.id in {"d00_board_length", "d01_board_width"}:
            axis = 0 if dimension.id == "d00_board_length" else 1
            assert dimension.value == pytest.approx(
                abs(_point(attached[1])[axis] - _point(attached[0])[axis]), abs=1e-9
            )
        elif dimension.id == "d02_board_thickness":
            assert dimension.value == pytest.approx(
                abs(attached[0]["centroid"][2] - attached[1]["centroid"][2]), abs=1e-9
            )
        elif dimension.id == "d13_height_above":
            assert dimension.value == pytest.approx(
                attached[1]["bbox"][5] - attached[0]["bbox"][5], abs=1e-9
            )
        elif dimension.id == "d14_height_below":
            assert dimension.value == pytest.approx(
                attached[0]["bbox"][2] - attached[1]["bbox"][2], abs=1e-9
            )


def test_entity_ids_and_cross_references_are_consistent() -> None:
    model = RawModel.model_validate(_json(FIXTURE_ROOT / "reference" / "raw_model.json"))
    ids: list[str] = [component.id for component in model.components]
    ids += [body.id for body in model.bodies]
    for body in model.bodies:
        ids += [face.id for face in body.faces]
        ids += [edge.id for edge in body.edges]
        face_ids = {face.id for face in body.faces}
        edge_ids = {edge.id for edge in body.edges}
        for face in body.faces:
            assert set(face.edge_ids) <= edge_ids
        for edge in body.edges:
            assert set(edge.face_ids) <= face_ids
        for face in body.faces:
            for edge_id in face.edge_ids:
                assert face.id in next(edge for edge in body.edges if edge.id == edge_id).face_ids
        for edge in body.edges:
            for face_id in edge.face_ids:
                assert edge.id in next(face for face in body.faces if face.id == face_id).edge_ids
    assert len(ids) == len(set(ids))


def test_siblings_have_the_requested_differences_and_sources_are_synthetic() -> None:
    reference = _json(FIXTURE_ROOT / "reference" / "raw_model.json")
    board_sibling = _json(FIXTURE_ROOT / "sibling_board_size" / "raw_model.json")
    moved_sibling = _json(FIXTURE_ROOT / "sibling_moved_holes" / "raw_model.json")
    connector_sibling = _json(FIXTURE_ROOT / "sibling_extra_connector" / "raw_model.json")
    assert board_sibling["bodies"][0]["bbox"][3:5] != reference["bodies"][0]["bbox"][3:5]
    assert moved_sibling["bodies"][0]["faces"] != reference["bodies"][0]["faces"]
    reference_connectors = [c for c in reference["components"] if c["name"].startswith("J")]
    sibling_connectors = [c for c in connector_sibling["components"] if c["name"].startswith("J")]
    assert len(sibling_connectors) == len(reference_connectors) + 1
    for path in FIXTURE_ROOT.rglob("raw_*.json"):
        payload = _json(path)
        assert payload["source"]["synthetic"] is True


def test_no_real_fixture_tree_exists_and_generation_is_byte_deterministic(tmp_path: Path) -> None:
    assert not (REPO_ROOT / "fixtures" / "real").exists()
    first = tmp_path / "first"
    second = tmp_path / "second"
    make_synthetic.generate_all(first)
    make_synthetic.generate_all(second)
    first_files = sorted(path.relative_to(first) for path in first.rglob("*.json"))
    second_files = sorted(path.relative_to(second) for path in second.rglob("*.json"))
    assert first_files == second_files
    for relative in first_files:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()


def test_view_boxes_match_the_model_projected_through_each_rotation() -> None:
    """Each view box is the model's overall box rotated into the view, scaled and centred."""

    model = RawModel.model_validate(_json(FIXTURE_ROOT / "reference" / "raw_model.json"))
    drawing = RawDrawing.model_validate(_json(FIXTURE_ROOT / "reference" / "raw_drawing.json"))
    lo = [min(body.bbox[axis] for body in model.bodies) for axis in range(3)]
    hi = [max(body.bbox[axis + 3] for body in model.bodies) for axis in range(3)]
    corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    for view in drawing.sheets[0].views:
        assert view.rotation is not None
        rows = (view.rotation[0:3], view.rotation[3:6], view.rotation[6:9])
        projected = [
            tuple(sum(row[i] * corner[i] for i in range(3)) for row in rows[:2])
            for corner in corners
        ]
        width = (max(p[0] for p in projected) - min(p[0] for p in projected)) * view.scale
        height = (max(p[1] for p in projected) - min(p[1] for p in projected)) * view.scale
        cx, cy = view.center
        expected = (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
        assert view.bbox == pytest.approx(expected, abs=1e-9), view.name


def test_side_view_keeps_model_z_pointing_up() -> None:
    drawing = RawDrawing.model_validate(_json(FIXTURE_ROOT / "reference" / "raw_drawing.json"))
    side = next(view for view in drawing.sheets[0].views if view.id == "v_side")
    assert side.rotation is not None
    assert side.rotation[3:6] == (0.0, 0.0, 1.0)
