from drawgen.assistant.checker import check_answer, ungrounded_arguments


def test_checker_rejects_invented_number() -> None:
    assert check_answer("Area is 12.5 mm2", [{"value": 12.5}])[0]
    assert not check_answer("Area is 13.5 mm2", [{"value": 12.5}])[0]


def test_checker_accepts_displayed_precision_only() -> None:
    assert check_answer("Area is 1234.57 mm2", [{"value": 1234.5678}])[0]
    assert check_answer("Area is 1235 mm2", [{"value": 1234.5678}])[0]
    assert not check_answer("Area is 1234.50 mm2", [{"value": 1234.5678}])[0]


def test_checker_counts_list_lengths_but_not_identifier_digits() -> None:
    result = {"items": [{"handle": "tag:6"}, {"handle": "tag:7"}]}
    assert check_answer("There are 2 faces.", [result])[0]
    assert not check_answer("There are 6 faces.", [result])[0]
    assert not check_answer("Face 7 is selected.", [{"id": "7"}])[0]


def test_tool_arguments_must_come_from_the_user_or_a_result() -> None:
    sources = ["Make a 100x60x20 box with a 10 mm hole", {"value": 12.5}]
    assert ungrounded_arguments({"width": 100.0, "depth": 60, "height": 20.0}, sources) == []
    assert ungrounded_arguments({"value": 12.5}, sources) == []
    assert ungrounded_arguments({"width": 999.0, "flag": True}, sources) == [999.0]
