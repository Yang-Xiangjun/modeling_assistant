from typing import Literal

import pytest

from drawgen.assistant.contracts import HarnessRequest
from drawgen.assistant.harness import CodexApiHarness, _parse_step


def test_harness_parser_accepts_direct_and_pi_message_json() -> None:
    assert _parse_step({"answer": "ok"}).answer == "ok"
    assert _parse_step({"message": {"content": '{"ask_user":"select a face"}'}}).ask_user == (
        "select a face"
    )
    assert (
        _parse_step({"type": "message", "content": [{"text": '{"answer":"done"}'}]}).answer
        == "done"
    )


def test_codex_api_adapter_uses_structured_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: object) -> Literal[False]:
            return False

        def read(self) -> bytes:
            return b'{"output_text":"{\\"answer\\":\\"done\\"}"}'

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    step = CodexApiHarness(api_key="test", base_url="http://example.test").select(HarnessRequest())
    assert step.answer == "done"
