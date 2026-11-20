"""Provider-neutral assistant and harness messages."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from drawgen.contracts.common import Contract


class ToolCall(Contract):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class AssistantStep(Contract):
    tool_calls: list[ToolCall] = Field(default_factory=list)
    answer: str | None = None
    ask_user: str | None = None

    @model_validator(mode="after")
    def exactly_one_action(self) -> AssistantStep:
        actions = (
            int(bool(self.tool_calls))
            + int(self.answer is not None)
            + int(self.ask_user is not None)
        )
        if actions != 1:
            raise ValueError(
                "AssistantStep must contain exactly one of tool_calls, answer, ask_user"
            )
        return self


class HarnessRequest(Contract):
    protocol: Literal["1"] = "1"
    conversation: list[dict[str, str]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    operation_plan: dict[str, Any] | None = None


class ToolSpec(Contract):
    name: str
    kind: Literal["read", "session", "change"]
    description: str
    args_schema: dict[str, Any] = Field(default_factory=dict)


class ToolExecution(Contract):
    ok: bool
    needs_confirmation: bool = False
    preview: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class TurnResult(Contract):
    answer: str | None = None
    ask_user: str | None = None
    tool_results: list[ToolExecution] = Field(default_factory=list)
