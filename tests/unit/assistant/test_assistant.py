from drawgen.assistant.agent import AssistantAgent
from drawgen.assistant.contracts import AssistantStep, HarnessRequest
from drawgen.assistant.harness import FakeHarness
from drawgen.backends.live_mock import MockLiveBackend
from drawgen.contracts.live import LiveMeasureResult, SelectedObject, Selection


class _NineRoundHarness:
    def __init__(self) -> None:
        self.rounds = 0

    def select(self, request: HarnessRequest) -> AssistantStep:
        if self.rounds < 9:
            identifier = f"m{self.rounds}"
            self.rounds += 1
            return AssistantStep(
                tool_calls=[
                    {
                        "tool": "measure",
                        "args": {
                            "requests": [{"id": identifier, "kind": "area", "a": "h-face"}]
                        },
                    }
                ]
            )
        return AssistantStep(answer="The area is 1.0 mm2.")


def test_agent_reads_selection_and_returns_only_tool_number() -> None:
    backend = MockLiveBackend(
        selection=Selection(
            items=[
                SelectedObject(
                    handle="h-face",
                    entity_kind="face",
                    object_type="Face",
                    properties={"area": 12.5},
                )
            ]
        ),
        measurements={"m0": LiveMeasureResult(id="m0", value=12.5, unit="mm2")},
    )
    harness = FakeHarness(
        [
            AssistantStep(tool_calls=[{"tool": "get_selection", "args": {}}]),
            AssistantStep(
                tool_calls=[
                    {
                        "tool": "measure",
                        "args": {"requests": [{"id": "m0", "kind": "area", "a": "h-face"}]},
                    }
                ]
            ),
            AssistantStep(answer="The area is 12.5 mm2."),
        ]
    )
    result = AssistantAgent(backend, harness).run("What is the area of this face?")
    assert result.answer == "The area is 12.5 mm2."
    assert len(backend.executed) == 0


def test_surface_request_measures_selected_body() -> None:
    backend = MockLiveBackend(
        selection=Selection(
            items=[
                SelectedObject(
                    handle="h-body",
                    entity_kind="body",
                    object_type="Body",
                    properties={"surface_area_mm2": 1234.5},
                )
            ]
        ),
        measurements={"m0": LiveMeasureResult(id="m0", value=1234.5, unit="mm2")},
    )

    result = AssistantAgent(backend, FakeHarness()).run(
        "What is the total surface area of the selected block?"
    )

    assert result.answer == "The measured surface area is 1234.5 mm2."


def test_volume_request_measures_selected_body() -> None:
    backend = MockLiveBackend(
        selection=Selection(
            items=[SelectedObject(handle="h-body", entity_kind="body", object_type="Body")]
        ),
        measurements={"v0": LiveMeasureResult(id="v0", value=120000.0, unit="mm3")},
    )

    result = AssistantAgent(backend, FakeHarness()).run(
        "What is the volume of the selected body?"
    )

    assert result.answer == "The measured volume is 120000.0 mm3."


def test_measurement_error_is_reported_without_retrying_until_a_limit() -> None:
    backend = MockLiveBackend(
        selection=Selection(
            items=[
                SelectedObject(
                    handle="h-face",
                    entity_kind="face",
                    object_type="Face",
                )
            ]
        ),
        measurements={"m0": LiveMeasureResult(id="m0", error="invalid face")},
    )
    harness = FakeHarness(
        [
            AssistantStep(tool_calls=[{"tool": "get_selection", "args": {}}]),
            AssistantStep(
                tool_calls=[
                    {
                        "tool": "measure",
                        "args": {"requests": [{"id": "m0", "kind": "area", "a": "h-face"}]},
                    }
                ]
            ),
        ]
    )

    result = AssistantAgent(backend, harness).run("What is the area of this face?")

    assert result.answer is None
    assert result.ask_user == "NX measurement failed: invalid face"
    assert len(result.tool_results) == 2


def test_agent_can_complete_after_more_than_eight_tool_rounds() -> None:
    backend = MockLiveBackend(
        measurements={
            f"m{index}": LiveMeasureResult(id=f"m{index}", value=1.0, unit="mm2")
            for index in range(9)
        }
    )

    harness = _NineRoundHarness()
    result = AssistantAgent(backend, harness).run("Measure the selected face area.")

    assert result.answer == "The area is 1.0 mm2."
    assert harness.rounds == 9


def test_change_requires_confirmation_and_sets_one_undo_mark() -> None:
    backend = MockLiveBackend()
    harness = FakeHarness(
        [AssistantStep(tool_calls=[{"tool": "show_entity", "args": {"handle": "h1"}}])]
    )
    result = AssistantAgent(backend, harness).run("Show this entity")
    assert result.ask_user is not None
    assert backend.executed == []

    harness = FakeHarness(
        [AssistantStep(tool_calls=[{"tool": "show_entity", "args": {"handle": "h1"}}])]
    )
    result = AssistantAgent(backend, harness).run("Show this entity", confirm=lambda _: True)
    assert result.ask_user is not None
    assert backend.executed == [("show_entity", {"handle": "h1"})]
    assert len(backend.undo_marks) == 1


def test_create_box_with_hole_uses_typed_change_tool() -> None:
    backend = MockLiveBackend()
    result = AssistantAgent(backend, FakeHarness()).run(
        "Create a 100 x 60 x 20 box with a 10 mm through-hole.", confirm=lambda _: True
    )
    assert result.answer == "Created the requested box with a centered through-hole in NX."
    assert backend.executed == [
        (
            "create_box_with_hole",
            {"width": 100.0, "depth": 60.0, "height": 20.0, "hole_diameter": 10.0},
        )
    ]


def test_create_box_with_hole_passes_requested_center_offsets() -> None:
    backend = MockLiveBackend()
    harness = FakeHarness(
        [
            AssistantStep(
                tool_calls=[
                    {
                        "tool": "create_box_with_hole",
                        "args": {
                            "width": 100.0,
                            "depth": 60.0,
                            "height": 20.0,
                            "hole_diameter": 10.0,
                            "hole_center_left": 10.0,
                            "hole_center_bottom": 10.0,
                        },
                    }
                ]
            )
        ]
    )

    result = AssistantAgent(backend, harness).run(
        "Create the box with the hole center 10 mm from the left and bottom boundaries.",
        confirm=lambda _: True,
    )

    assert result.ask_user is None
    assert backend.executed == [
        (
            "create_box_with_hole",
            {
                "width": 100.0,
                "depth": 60.0,
                "height": 20.0,
                "hole_diameter": 10.0,
                "hole_center_left": 10.0,
                "hole_center_bottom": 10.0,
            },
        )
    ]
