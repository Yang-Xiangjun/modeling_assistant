"""Every contract round-trips through JSON and agrees with its exported JSON Schema."""

import json
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError

from drawgen.contracts.common import Contract
from drawgen.contracts.registry import ALL, VERSIONED
from tests.contract.samples import SAMPLES

NAMES = sorted(ALL)


def test_every_contract_has_a_sample() -> None:
    assert set(SAMPLES) == set(ALL)


@pytest.mark.parametrize("name", NAMES)
def test_round_trip(name: str) -> None:
    model = ALL[name]
    first = model.model_validate(SAMPLES[name])
    text = first.model_dump_json()
    second = model.model_validate_json(text)
    assert second == first
    # The sample spells out every field, so the dump must reproduce it exactly.
    assert json.loads(text) == SAMPLES[name]


@pytest.mark.parametrize("name", NAMES)
def test_dump_validates_against_json_schema(name: str) -> None:
    model = ALL[name]
    payload = json.loads(model.model_validate(SAMPLES[name]).model_dump_json())
    jsonschema.validate(payload, model.model_json_schema(by_alias=True))


@pytest.mark.parametrize("name", sorted(VERSIONED))
def test_schema_string(name: str) -> None:
    model = VERSIONED[name]
    dumped = model.model_validate(SAMPLES[name]).model_dump(mode="json")
    assert dumped["schema"] == f"{name}/0"
    assert "schema_" not in dumped
    wrong = {**SAMPLES[name], "schema": f"{name}/999"}
    with pytest.raises(ValidationError):
        model.model_validate(wrong)


@pytest.mark.parametrize("name", NAMES)
def test_unknown_fields_are_rejected(name: str) -> None:
    with pytest.raises(ValidationError):
        ALL[name].model_validate({**SAMPLES[name], "surprise": 1})


def _all_models() -> set[type[Contract]]:
    found: set[type[Contract]] = set()
    stack = list(Contract.__subclasses__())
    while stack:
        cls = stack.pop()
        if cls not in found:
            found.add(cls)
            stack.extend(cls.__subclasses__())
    return found


def test_every_model_forbids_extras_and_non_finite_numbers() -> None:
    models = _all_models()
    assert len(models) > 50
    for cls in models:
        assert cls.model_config.get("extra") == "forbid", cls
        assert cls.model_config.get("allow_inf_nan") is False, cls


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_non_finite_values_are_rejected(bad: float) -> None:
    sample: dict[str, Any] = json.loads(json.dumps(SAMPLES["candidate_set"]))
    sample["dimensions"][0]["expected_value"] = bad
    with pytest.raises(ValidationError):
        ALL["candidate_set"].model_validate(sample)


def test_edit_set_is_closed() -> None:
    sample: dict[str, Any] = json.loads(json.dumps(SAMPLES["findings"]))
    sample["results"][0]["edits"] = [{"op": "set_dimension_value", "id": "d0", "value": 1.0}]
    with pytest.raises(ValidationError):
        ALL["findings"].model_validate(sample)
