"""Tests for deterministic JSON I/O."""

import json
from pathlib import Path

import pytest
from drawgen_shared.jsonio import canonical_json, read_json, sha256_canonical, write_json


def test_canonical_json_is_sorted_compact_and_unicode_safe() -> None:
    assert canonical_json({"z": 1, "a": "café", "nested": {"b": 2, "a": 1}}) == (
        '{"a":"café","nested":{"a":1,"b":2},"z":1}'
    )
    assert sha256_canonical({"a": 1, "b": [2, 3]}) == sha256_canonical({"b": [2, 3], "a": 1})
    with pytest.raises(ValueError):
        canonical_json({"value": float("nan")})


def test_write_and_read_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "payload.json"
    payload = {"z": "é", "a": [1, True, None]}
    write_json(path, payload)
    assert (
        path.read_text(encoding="utf-8")
        == '{\n  "a": [\n    1,\n    true,\n    null\n  ],\n  "z": "é"\n}\n'
    )
    assert read_json(path) == payload
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    with pytest.raises(ValueError):
        write_json(path, {"value": float("inf")})
