"""Deterministic request classification and operation-plan construction."""

from __future__ import annotations

import re

from drawgen.assistant.api_search import (
    ApiCatalog,
    expand_synonyms,
    search_nx_api,
    validate_candidate,
)
from drawgen.contracts.operation_plan import ApiCandidate, OperationPlan, PlanStep

_COMPLEX_MARKERS = (
    " then ",
    " after ",
    " before ",
    " while ",
    " if ",
    " followed by ",
    " unless ",
)
_ACTION_WORDS = {
    "create",
    "make",
    "build",
    "edit",
    "change",
    "measure",
    "calculate",
    "update",
    "export",
    "save",
    "hide",
    "show",
    "isolate",
    "add",
    "remove",
}


def classify_request(request: str) -> str:
    """Classify a request before API discovery or NX execution."""

    text = " ".join(request.split()).strip()
    if not text:
        return "ambiguous"
    lowered = f" {text.lower()} "
    action_count = sum(
        1 for word in _ACTION_WORDS if re.search(rf"\b{re.escape(word)}\b", lowered)
    )
    if (
        len(text) > 160
        or action_count > 1
        or any(marker in lowered for marker in _COMPLEX_MARKERS)
    ):
        return "complex"
    if not re.search(
        r"\b(what|which|how|tell|show|measure|calculate|create|make|build|fit|orient)\b",
        lowered,
    ):
        return "ambiguous"
    return "simple"


def clarification_questions(request: str, complexity: str) -> list[str]:
    """Return concise clarification prompts for complex or ambiguous requests."""

    if complexity == "simple":
        return []
    questions = ["What exact result should NX return or change?"]
    if not re.search(
        r"\b(selected|this|that|current|body|face|edge|part|model|cylinder|box)\b",
        request.lower(),
    ):
        questions.append("Which NX object, part, or selection is the target?")
    if complexity == "complex":
        questions.append("What units or output format should be used?")
    return questions


def build_operation_plan(request: str) -> OperationPlan:
    """Build an initial plan without executing NX or choosing an API."""

    normalized = " ".join(request.split()).strip()
    complexity = classify_request(normalized)
    questions = clarification_questions(normalized, complexity)
    action = "inspect_or_operate"
    if re.search(
        r"\b(volume|mass|area|surface|length|radius|diameter|distance|angle|centroid)\b",
        normalized,
        re.I,
    ):
        action = "measure"
    elif re.search(r"\b(create|make|build|edit|change|update|export|save)\b", normalized, re.I):
        action = "operate"
    step = PlanStep(
        id="step-1",
        action=action,
        description=normalized or "Clarify the requested NX operation.",
        entity_requirements=[],
        preconditions=["Interactive NX session is available."],
        api_queries=expand_synonyms(normalized),
        expected_outputs=["typed NX result"],
    )
    return OperationPlan(
        request=normalized,
        goal=normalized or "Clarify the requested NX operation.",
        complexity=complexity,
        clarification_required=bool(questions),
        clarification_questions=questions,
        steps=[step],
    )


def _required_terms(query: str) -> tuple[str, ...]:
    """Return a small evidence constraint for a measurable plan step."""

    text = query.lower()
    if "mass properties" in text:
        return ("mass", "properties")
    if "surface area" in text:
        return ("area",)
    for term in ("volume", "area", "length", "radius", "diameter", "distance", "angle"):
        if term in text:
            return (term,)
    return ()


def discover_api_candidates(
    plan: OperationPlan,
    *,
    catalog: ApiCatalog | None = None,
    nx_version: str | None = None,
    limit: int = 4,
) -> OperationPlan:
    """Attach local NXOpen evidence before the harness selects tools."""

    if plan.clarification_required:
        return plan
    evidence: dict[str, ApiCandidate] = {}
    updated_steps: list[PlanStep] = []
    for step in plan.steps:
        validated_ids: list[str] = []
        for query in step.api_queries:
            candidates = search_nx_api(query, catalog=catalog, limit=limit)
            for candidate in candidates:
                checked = validate_candidate(
                    candidate,
                    required_terms=_required_terms(query),
                    nx_version=nx_version,
                )
                evidence[checked.id] = checked
                if checked.status == "validated" and checked.id not in validated_ids:
                    validated_ids.append(checked.id)
        updated_steps.append(step.model_copy(update={"api_candidate_ids": validated_ids}))
    candidates = list(evidence.values())
    assumptions = list(plan.assumptions)
    if candidates:
        assumptions.append(f"Attached {len(candidates)} local NXOpen API candidates.")
    else:
        assumptions.append("No local NXOpen API candidate matched this step.")
    return plan.model_copy(
        update={
            "steps": updated_steps,
            "api_candidates": candidates,
            "assumptions": assumptions,
        }
    )
