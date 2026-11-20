"""The tool list offered to the LLM matches what the connected bridge runs."""

from __future__ import annotations

import pytest

from drawgen.assistant.tools import ToolError, ToolRegistry
from drawgen.backends.bridge import LEGACY_BRIDGE_COMMANDS
from drawgen.backends.live_mock import MockLiveBackend


def _names(registry: ToolRegistry) -> set[str]:
    return {spec["name"] for spec in registry.specs()}


def test_unsupported_tools_are_hidden_and_refused() -> None:
    registry = ToolRegistry(MockLiveBackend(supported=LEGACY_BRIDGE_COMMANDS))
    names = _names(registry)

    assert {"get_selection", "measure", "create_box_with_hole", "hide_entity"} <= names
    assert "search_nx_api" in names  # local tool, needs no bridge command
    for missing in ("list", "open_part", "orient_view", "edit_expression", "export_pdf"):
        assert missing not in names
    with pytest.raises(ToolError, match="does not support edit_expression"):
        registry.execute("edit_expression", {"handle": "h", "value": 1.0}, confirmed=True)


def test_unknown_capabilities_keep_every_tool() -> None:
    registry = ToolRegistry(MockLiveBackend())
    assert {"list", "edit_expression", "export_pdf"} <= _names(registry)
