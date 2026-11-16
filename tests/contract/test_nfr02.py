"""NFR-02: no dimension value can originate from an LLM.

DrawingPlan and PlanSelection must have no field able to hold a dimension
value. The test walks their JSON Schemas and collects every place a number
(or an untyped value, which could hide a number) can appear, then compares
that with an exact allow-list of layout numbers. Adding any numeric or
untyped field to either model fails here and needs a decision note.
"""

from typing import Any

from drawgen.contracts.candidate_set import CandidateSet
from drawgen.contracts.common import Contract
from drawgen.contracts.drawing_plan import DrawingPlan, PlanSelection

# Layout numbers set by core/layout.py, plus the plan version. Nothing else.
DRAWING_PLAN_NUMBERS = {
    ".plan_version",
    ".sheet.width",
    ".sheet.height",
    ".views[].scale",
    ".views[].center[]",
    ".dimensions[].placement.rank",
    ".notes[].anchor[]",
}

_COMBINATORS = ("anyOf", "oneOf", "allOf")


def number_paths(model: type[Contract]) -> set[str]:
    """Every path in the model's JSON Schema where a number or an untyped value can sit."""
    root = model.model_json_schema(by_alias=True)
    defs: dict[str, Any] = root.get("$defs", {})
    found: set[str] = set()

    def walk(node: Any, path: str) -> None:
        if node is True or node == {}:
            found.add(path + "<any>")
            return
        if not isinstance(node, dict):
            return
        if "$ref" in node:
            walk(defs[node["$ref"].rsplit("/", 1)[-1]], path)
            return
        typ = node.get("type")
        types = typ if isinstance(typ, list) else [typ]
        if "number" in types or "integer" in types:
            found.add(path)
        for key in _COMBINATORS:
            for sub in node.get(key, []):
                walk(sub, path)
        for name, sub in node.get("properties", {}).items():
            walk(sub, f"{path}.{name}")
        if "items" in node:
            walk(node["items"], path + "[]")
        for sub in node.get("prefixItems", []):
            walk(sub, path + "[]")
        extra = node.get("additionalProperties")
        if extra is not None and extra is not False:
            walk(extra, path + "{}")
        if "object" in types and "properties" not in node and extra is None:
            found.add(path + "<any>")
        described = typ is not None or any(k in node for k in (*_COMBINATORS, "const", "enum"))
        if not described:
            found.add(path + "<any>")

    walk(root, "")
    return found


def test_walker_finds_dimension_values_where_they_exist() -> None:
    # Guards the test itself: the walker must see expected_value on a candidate.
    assert ".dimensions[].expected_value" in number_paths(CandidateSet)


def test_plan_selection_has_no_number_at_all() -> None:
    assert number_paths(PlanSelection) == set()


def test_drawing_plan_numbers_are_exactly_the_layout_numbers() -> None:
    assert number_paths(DrawingPlan) == DRAWING_PLAN_NUMBERS


def test_no_value_like_field_names() -> None:
    banned = ("value", "expected", "measure", "nominal", "length", "diameter", "radius", "angle")
    allowed = {".title_block{}.value"}  # a string with a recorded source, checked below

    def names(model: type[Contract]) -> set[str]:
        root = model.model_json_schema(by_alias=True)
        defs = root.get("$defs", {})
        out: set[str] = set()

        def walk(node: Any, path: str) -> None:
            if not isinstance(node, dict):
                return
            if "$ref" in node:
                walk(defs[node["$ref"].rsplit("/", 1)[-1]], path)
                return
            for key in _COMBINATORS:
                for sub in node.get(key, []):
                    walk(sub, path)
            for name, sub in node.get("properties", {}).items():
                out.add(f"{path}.{name}")
                walk(sub, f"{path}.{name}")
            if isinstance(node.get("items"), dict):
                walk(node["items"], path + "[]")
            if isinstance(node.get("additionalProperties"), dict):
                walk(node["additionalProperties"], path + "{}")

        walk(root, "")
        return out

    for model in (DrawingPlan, PlanSelection):
        offenders = {
            p for p in names(model) if any(b in p.rsplit(".", 1)[-1] for b in banned)
        } - allowed
        assert offenders == set(), (model.__name__, offenders)

    title_value = DrawingPlan.model_json_schema()["$defs"]["TitleBlockEntry"]["properties"]["value"]
    assert title_value["type"] == "string"
