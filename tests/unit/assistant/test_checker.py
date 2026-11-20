from drawgen.assistant.checker import check_answer


def test_checker_rejects_invented_number() -> None:
    assert check_answer("Area is 12.5 mm2", [{"value": 12.5}])[0]
    assert not check_answer("Area is 13.5 mm2", [{"value": 12.5}])[0]
