"""Focused tests for plan-first Branch C request handling."""

from pathlib import Path

from drawgen.assistant.agent import AssistantAgent
from drawgen.assistant.api_search import (
    ApiCatalog,
    expand_synonyms,
    search_nx_api,
    validate_candidate,
)
from drawgen.assistant.contracts import AssistantStep
from drawgen.assistant.harness import FakeHarness
from drawgen.assistant.planning import (
    build_operation_plan,
    classify_request,
    discover_api_candidates,
)
from drawgen.backends.live_mock import MockLiveBackend


def test_complex_request_is_marked_for_clarification() -> None:
    request = "Create a box and then measure its volume after changing the hole."

    plan = build_operation_plan(request)

    assert classify_request(request) == "complex"
    assert plan.complexity == "complex"
    assert plan.clarification_required is True
    assert plan.clarification_questions
    assert plan.steps[0].action == "measure"


def test_ambiguous_request_asks_for_goal_and_target() -> None:
    plan = build_operation_plan("Do something with NX")

    assert plan.complexity == "ambiguous"
    assert plan.clarification_required is True
    assert any("result" in question.lower() for question in plan.clarification_questions)
    assert any("target" in question.lower() for question in plan.clarification_questions)


def test_clear_operations_and_other_languages_are_not_blocked() -> None:
    for request in (
        "hide this body",
        "isolate the selected body",
        "save the part",
        "update the model",
        "Area of the face?",
        "选中面的面积是多少",
    ):
        assert classify_request(request) == "simple", request


def test_clarification_answer_completes_the_original_request() -> None:
    backend = MockLiveBackend()
    harness = FakeHarness([AssistantStep(answer="Done.")])
    agent = AssistantAgent(backend, harness)

    first = agent.run("Do something with NX")
    assert first.ask_user is not None and "clarify" in first.ask_user

    second = agent.run("the selected body")
    assert second.answer == "Done."
    assert agent.pending_clarification is None


def test_volume_request_expands_to_mass_property_search_terms() -> None:
    plan = build_operation_plan("Tell me the volume of the selected cylinder.")

    assert plan.complexity == "simple"
    assert plan.clarification_required is False
    assert plan.steps[0].action == "measure"
    queries = {query.lower() for query in plan.steps[0].api_queries}
    assert {"volume", "solid volume", "mass properties"}.issubset(queries)


def test_api_search_uses_synonyms_and_validates_catalog_evidence(tmp_path: Path) -> None:
    index = tmp_path / "index.tsv"
    index.write_text(
        "kind\tfull_name\tsummary\tasset_id\tguid\n"
        "method\tNXOpen.MeasureManager.NewMassProperties\t"
        "Create mass properties for bodies\tNewMassProperties\tg0\n",
        encoding="utf-8",
    )
    catalog = ApiCatalog(index)

    assert "mass properties" in expand_synonyms("volume")
    candidates = search_nx_api("volume", catalog=catalog)
    assert candidates
    validated = validate_candidate(
        candidates[0], required_terms=("mass", "properties"), nx_version="2506"
    )
    assert validated.status == "validated"
    assert validated.nx_version == "2506"


def test_plan_attaches_validated_api_candidates(tmp_path: Path) -> None:
    index = tmp_path / "index.tsv"
    index.write_text(
        "kind\tfull_name\tsummary\tasset_id\tguid\n"
        "method\tNXOpen.MeasureManager.NewMassProperties\t"
        "Create mass properties for bodies\tNewMassProperties\tg0\n"
        "property\tNXOpen.MeasureBodies.Volume\tReturns the volume\tVolume\tg1\n",
        encoding="utf-8",
    )
    plan = discover_api_candidates(
        build_operation_plan("Tell me the volume of the selected body."),
        catalog=ApiCatalog(index),
        nx_version="2506",
    )

    assert plan.api_candidates
    assert plan.steps[0].api_candidate_ids
    assert any(candidate.status == "validated" for candidate in plan.api_candidates)
