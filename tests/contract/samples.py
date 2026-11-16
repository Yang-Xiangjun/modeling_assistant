"""One JSON-shaped sample per contract, with every optional field populated where practical."""

from typing import Any

FP_FACE: dict[str, Any] = {
    "kind": "face",
    "geom": "cylinder",
    "size": 15.07964,
    "centroid": [5.0, 5.0, 0.8],
    "direction": [0.0, 0.0, 1.0],
    "radius": 1.5,
    "bbox": [3.5, 3.5, 0.0, 6.5, 6.5, 1.6],
    "component_path": "root/board",
}
FP_EDGE: dict[str, Any] = {
    "kind": "edge",
    "geom": "line",
    "size": 80.0,
    "centroid": [40.0, 0.0, 1.6],
    "direction": [1.0, 0.0, 0.0],
    "radius": None,
    "bbox": [0.0, 0.0, 1.6, 80.0, 0.0, 1.6],
    "component_path": None,
}
IDENTITY3 = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
IDENTITY4 = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
TOLERANCE = {"type": "bilateral", "upper": 0.1, "lower": -0.1}
APPENDED = {"before": "4X", "after": "THRU", "above": "", "below": ""}
NOTE = {"id": "n0", "text": "NOTE 1", "origin": [20.0, 20.0], "view_id": None, "has_leader": False}
TABLE = {"id": "t0", "kind": "title_block", "origin": [300.0, 10.0], "rows": [["TITLE", "X"]]}
VIEW = {
    "id": "v0",
    "name": "TOP",
    "kind": "base",
    "parent_id": None,
    "model_view": "Top",
    "rotation": IDENTITY3,
    "scale": 1.0,
    "center": [150.0, 180.0],
    "bbox": [100.0, 150.0, 200.0, 210.0],
    "representation": "exact",
    "out_of_date": False,
}

SAMPLES: dict[str, dict[str, Any]] = {
    "raw_model": {
        "schema": "raw_model/0",
        "source": {
            "path": "synthetic/ref.prt",
            "units": "mm",
            "nx_version": None,
            "extracted_at": "2026-11-16T00:00:00Z",
            "synthetic": True,
            "attributes": {"PART_NO": "X-1"},
        },
        "components": [
            {
                "id": "c0",
                "parent_id": None,
                "name": "root",
                "part_name": "ref",
                "attributes": {},
                "transform": IDENTITY4,
                "suppressed": False,
            }
        ],
        "bodies": [
            {
                "id": "c0.b0",
                "component_id": "c0",
                "kind": "solid",
                "bbox": [0.0, 0.0, 0.0, 80.0, 60.0, 1.6],
                "volume": 7680.0,
                "faces": [
                    {
                        "id": "c0.b0.f0",
                        "geom": "cylinder",
                        "area": 15.07964,
                        "centroid": [5.0, 5.0, 0.8],
                        "direction": [0.0, 0.0, 1.0],
                        "axis_point": [5.0, 5.0, 0.0],
                        "radius": 1.5,
                        "half_angle": None,
                        "convex": False,
                        "bbox": [3.5, 3.5, 0.0, 6.5, 6.5, 1.6],
                        "edge_ids": ["c0.b0.e0"],
                    }
                ],
                "edges": [
                    {
                        "id": "c0.b0.e0",
                        "geom": "circle",
                        "length": 9.424778,
                        "start": None,
                        "end": None,
                        "center": [5.0, 5.0, 1.6],
                        "direction": [0.0, 0.0, 1.0],
                        "radius": 1.5,
                        "face_ids": ["c0.b0.f0"],
                    }
                ],
            }
        ],
    },
    "raw_drawing": {
        "schema": "raw_drawing/0",
        "source": {
            "path": "synthetic/ref_dwg.prt",
            "nx_version": None,
            "extracted_at": "2026-11-16T00:00:00Z",
            "synthetic": True,
            "model_part": "synthetic/ref.prt",
            "attributes": {},
        },
        "sheets": [
            {
                "id": "s0",
                "name": "SHT1",
                "width": 420.0,
                "height": 297.0,
                "scale": 1.0,
                "projection": "first",
                "standard": "ISO",
                "views": [VIEW],
                "dimensions": [
                    {
                        "id": "d0",
                        "view_id": "v0",
                        "kind": "linear",
                        "direction": "horizontal",
                        "value": 80.0,
                        "text": "80",
                        "text_overridden": False,
                        "appended_text": APPENDED,
                        "tolerance": TOLERANCE,
                        "origin": [150.0, 220.0],
                        "bbox": [145.0, 218.0, 155.0, 222.0],
                        "retained": False,
                        "attachments": [
                            {
                                "index": 0,
                                "entity_kind": "edge",
                                "fingerprint": FP_EDGE,
                                "point": [0.0, 0.0, 1.6],
                                "point_kind": "end",
                                "view_id": "v0",
                                "trace_note": None,
                            },
                            {
                                "index": 1,
                                "entity_kind": None,
                                "fingerprint": None,
                                "point": None,
                                "point_kind": None,
                                "view_id": None,
                                "trace_note": "object is not a model entity",
                            },
                        ],
                    }
                ],
                "notes": [NOTE],
                "tables": [TABLE],
            }
        ],
    },
    "feature_graph": {
        "schema": "feature_graph/0",
        "model_hash": "abc",
        "pack": "demo",
        "part_class": "prismatic",
        "frame": {
            "origin": [0.0, 0.0, 0.0],
            "x": [1.0, 0.0, 0.0],
            "y": [0.0, 1.0, 0.0],
            "z": [0.0, 0.0, 1.0],
            "basis": "bounding_rectangle",
        },
        "features": [
            {
                "id": "f0",
                "type": "hole",
                "role": "demo.mounting_hole",
                "role_source": "rule",
                "role_confidence": 0.8,
                "params": {"x": 5.0, "y": 5.0, "diameter": 3.0, "through": True, "tags": ["a", 1]},
                "fingerprints": [FP_FACE],
                "component_id": "c0",
                "members": [],
                "attributes": {"k": "v"},
            }
        ],
        "relations": [{"type": "coaxial", "a": "f0", "b": "f0", "params": {"tol": 0.001}}],
    },
    "drawing_graph": {
        "schema": "drawing_graph/0",
        "drawing_hash": "d",
        "model_hash": "m",
        "sheets": [
            {
                "id": "s0",
                "width": 420.0,
                "height": 297.0,
                "scale": 1.0,
                "projection": "first",
                "standard": "ISO",
                "views": [{**VIEW, "direction_in_frame": "+Z"}],
                "dimensions": [
                    {
                        "id": "g0",
                        "raw_id": "d0",
                        "view_id": "v0",
                        "kind": "linear",
                        "direction": "horizontal",
                        "value": 80.0,
                        "feature_refs": [{"feature_id": "f0", "entity": "edge:min_x"}],
                        "role_signature": "demo.board:length",
                        "tolerance": TOLERANCE,
                        "appended_text": APPENDED,
                        "placement": {"side": "above", "rank": 0},
                    }
                ],
                "notes": [NOTE],
                "tables": [TABLE],
            }
        ],
        "unlinked": [{"dimension_id": "d9", "reason": "attachment not traced"}],
    },
    "convention_profile": {
        "schema": "convention_profile/0",
        "reference_hash": "r",
        "pack": "demo",
        "template": None,
        "sheet": {"width": 420.0, "height": 297.0},
        "standard": "ISO",
        "projection": "first",
        "views": [
            {
                "key": "top",
                "kind": "base",
                "direction_in_frame": "+Z",
                "parent_key": None,
                "scale": 1.0,
                "anchor": [0.35, 0.6],
            }
        ],
        "datum": {
            "x_from": {"role": "demo.mounting_hole", "entity": "min_x"},
            "y_from": {"role": "demo.mounting_hole", "entity": "min_y"},
        },
        "dimension_rules": [
            {
                "role_signature": "demo.mounting_hole:position_x",
                "dim_kind": "ordinate",
                "scheme": "ordinate",
                "view_key": "top",
                "placement_side": "below",
                "observed": 4,
                "example_raw_ids": ["d1", "d2"],
            }
        ],
        "notes": [{"text": "NOTE 1", "anchor": [0.05, 0.05], "carry": "flag"}],
        "tolerances_seen": [{"role_signature": "demo.board:length", "tolerance": TOLERANCE}],
        "unlinked_count": 1,
    },
    "correspondence": {
        "schema": "correspondence/0",
        "target_hash": "t",
        "reference_hash": "r",
        "pairs": [
            {"target_id": "f0", "reference_id": "f0", "method": "attribute", "confidence": 1.0}
        ],
        "target_only": ["f7"],
        "reference_only": ["f8"],
    },
    "candidate_set": {
        "schema": "candidate_set/0",
        "target_hash": "t",
        "views": [
            {
                "id": "vc0",
                "kind": "base",
                "direction_in_frame": "+Z",
                "parent_id": None,
                "scale_options": [1.0, 2.0],
                "rule_id": "view.top",
            }
        ],
        "dimensions": [
            {
                "id": "dc0",
                "role_signature": "demo.board:length",
                "dim_kind": "linear",
                "direction": "horizontal",
                "feature_refs": [{"feature_id": "f0", "entity": "edge:min_x"}],
                "view_ids": ["vc0"],
                "expected_value": 80.0,
                "required": True,
                "rule_id": "DEMO-01",
                "source": "measured",
            }
        ],
    },
    "drawing_plan": {
        "schema": "drawing_plan/0",
        "plan_version": 1,
        "target_hash": "t",
        "pack": "demo",
        "template": None,
        "sheet": {"width": 420.0, "height": 297.0},
        "standard": "ISO",
        "projection": "first",
        "views": [{"id": "v0", "candidate_id": "vc0", "scale": 1.0, "center": [150.0, 180.0]}],
        "dimensions": [
            {
                "id": "d0",
                "candidate_id": "dc0",
                "view_id": "v0",
                "scheme_group": "g1",
                "placement": {"side": "above", "rank": 0},
            }
        ],
        "notes": [
            {
                "id": "n0",
                "text": "NOTE 1",
                "anchor": [0.05, 0.05],
                "source": "reference_convention",
                "flagged": True,
            }
        ],
        "title_block": {"TITLE": {"value": "X", "source": "attribute:DB_PART_NAME"}},
        "review_flags": [{"id": "rf0", "kind": "note", "message": "check", "refs": ["n0"]}],
        "provenance": {"planner": "rules", "model": None, "prompt_hash": None},
    },
    "plan_selection": {
        "schema": "plan_selection/0",
        "view_candidate_ids": ["vc0"],
        "dimension_choices": [{"candidate_id": "dc0", "view_candidate_id": "vc0"}],
        "role_assignments": [{"feature_id": "f0", "role": "demo.mounting_hole"}],
        "review_notes": ["f3 looks like a tooling hole"],
    },
    "execution_job": {
        "schema": "execution_job/0",
        "plan_version": 1,
        "target_part": "C:/data/t.prt",
        "template": None,
        "output_drawing": "C:/runs/1/t_dwg.prt",
        "sheet": {
            "width": 420.0,
            "height": 297.0,
            "scale": 1.0,
            "projection": "first",
            "standard": "ISO",
        },
        "views": [
            {
                "id": "v0",
                "kind": "base",
                "parent_id": None,
                "rotation": IDENTITY3,
                "scale": 1.0,
                "center": [150.0, 180.0],
                "representation": "exact",
            }
        ],
        "dimensions": [
            {
                "id": "d0",
                "view_id": "v0",
                "dim_kind": "linear",
                "direction": "horizontal",
                "attachments": [
                    {"fingerprint": FP_EDGE, "point_kind": "end"},
                    {"fingerprint": FP_FACE, "point_kind": None},
                ],
                "origin": [150.0, 220.0],
                "scheme_group": None,
            }
        ],
        "notes": [{"id": "n0", "text": "NOTE 1", "origin": [20.0, 20.0]}],
        "title_block": {"TITLE": "X"},
        "export": ["pdf", "dxf"],
    },
    "execution_report": {
        "schema": "execution_report/0",
        "plan_version": 1,
        "drawing_part": "C:/runs/1/t_dwg.prt",
        "nx_version": "NX 2406",
        "saved": False,
        "views": [
            {
                "id": "v0",
                "created": True,
                "error": None,
                "name": "TOP",
                "bbox": [100.0, 150.0, 200.0, 210.0],
                "scale": 1.0,
                "out_of_date": False,
            }
        ],
        "dimensions": [
            {
                "id": "d0",
                "created": True,
                "error": None,
                "value": 80.0,
                "text": "80",
                "associative": True,
                "retained": False,
                "bbox": [145.0, 218.0, 155.0, 222.0],
            },
            {
                "id": "d1",
                "created": False,
                "error": "unresolved",
                "value": None,
                "text": None,
                "associative": None,
                "retained": None,
                "bbox": None,
            },
        ],
        "unresolved": [{"dimension_id": "d1", "attachment_index": 0, "reason": "ambiguous"}],
        "exports": [{"format": "pdf", "path": "C:/runs/1/t.pdf"}],
    },
    "findings": {
        "schema": "findings/0",
        "plan_version": 1,
        "results": [
            {
                "rule_id": "V-05",
                "status": "fail",
                "message": "overlap",
                "refs": ["d0", "d1"],
                "edits": [
                    {"op": "move_dimension", "id": "d0", "side": "below", "rank": 1},
                    {"op": "move_view", "id": "v0", "center": [160.0, 180.0]},
                    {"op": "set_view_scale", "id": "v0", "scale": 0.5},
                    {"op": "set_sheet", "width": 594.0, "height": 420.0},
                    {"op": "add_dimension", "candidate_id": "dc1", "view_id": "v0"},
                    {"op": "remove_dimension", "id": "d1"},
                    {"op": "switch_view", "dimension_id": "d0", "view_id": "v1"},
                    {"op": "add_view", "candidate_id": "vc1"},
                    {"op": "flag", "message": "needs a person", "refs": ["d0"]},
                ],
            }
        ],
        "summary": {"pass": 3, "fail": 1, "warn": 0, "review": 0},
    },
    "run_manifest": {
        "schema": "run_manifest/0",
        "run_id": "2026-11-16_001",
        "created_at": "2026-11-16T00:00:00Z",
        "inputs": {"target": "t.prt", "reference_model": "r.prt", "reference_drawing": "r_dwg.prt"},
        "config": {
            "backend": "mock",
            "pack": "demo",
            "rules_only": True,
            "tolerances": {
                "linear_mm": 0.001,
                "angular_deg": 0.01,
                "fingerprint_size_rel": 1e-6,
                "fingerprint_size_abs": 1e-4,
                "fingerprint_centroid_mm": 0.001,
                "fingerprint_direction_rad": 1e-4,
                "fingerprint_radius_mm": 0.001,
            },
        },
        "artifacts": {"raw_model": {"path": "raw_model.json", "sha256": "00"}},
        "steps": [{"node": "intake", "started": "t0", "ended": "t1", "status": "ok"}],
        "llm_calls": [{"node": "plan_llm", "model": "m", "prompt_hash": "p", "response_hash": "r"}],
    },
    "worker_job": {
        "protocol": "1",
        "command": "extract_model",
        "inputs": {"part_path": "C:/data/ref.prt"},
        "output_dir": "C:/runs/1/extract_model",
        "options": {"save_on_failure": False},
    },
    "worker_status": {
        "ok": False,
        "command": "ping",
        "error": {"type": "ImportError", "message": "no NXOpen", "traceback": "Traceback ..."},
        "duration_s": 0.1,
        "nx_version": None,
        "python_version": "3.10.11",
        "log": ["start"],
    },
    "ping_result": {"nx_version": "v2406", "python_version": "3.10.11"},
    "measure_results": {
        "results": [
            {"id": "m0", "value": 80.0, "error": None},
            {"id": "m1", "value": None, "error": "no_match"},
        ]
    },
    "export_result": {"exports": [{"format": "dxf", "path": "C:/runs/1/t.dxf"}]},
}
