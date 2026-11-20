"""Provider-neutral assistant turn loop."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from drawgen.assistant.checker import check_answer
from drawgen.assistant.contracts import HarnessRequest, TurnResult
from drawgen.assistant.harness import HarnessAdapter
from drawgen.assistant.log import SessionLog
from drawgen.assistant.planning import build_operation_plan, discover_api_candidates
from drawgen.assistant.tools import ToolError, ToolRegistry
from drawgen.backends.live import LiveBackend


class AssistantAgent:
    def __init__(
        self,
        backend: LiveBackend,
        harness: HarnessAdapter,
        *,
        log: SessionLog | None = None,
    ) -> None:
        self.backend = backend
        self.harness = harness
        self.registry = ToolRegistry(backend)
        self.log = log
        self.conversation: list[dict[str, str]] = []

    def run(
        self,
        user_message: str,
        *,
        confirm: Callable[[str], bool] | None = None,
    ) -> TurnResult:
        self.conversation.append({"role": "user", "content": user_message})
        if self.log:
            self.log.append("user_message", content=user_message)
        operation_plan = discover_api_candidates(build_operation_plan(user_message))
        if self.log:
            self.log.append("operation_plan", plan=operation_plan.model_dump(mode="json"))
        if operation_plan.clarification_required:
            questions = "\n".join(
                f"- {question}" for question in operation_plan.clarification_questions
            )
            return TurnResult(
                ask_user=f"Before I plan this NX operation, please clarify:\n{questions}"
            )
        results: list[Any] = []
        sources: list[Any] = [user_message]
        issued_calls: set[str] = set()
        failed_calls: set[str] = set()
        while True:
            context = self.backend.get_context().model_dump(mode="json")
            request = HarnessRequest(
                conversation=self.conversation,
                context=context,
                tools=self.registry.specs(),
                tool_results=results,
                operation_plan=operation_plan.model_dump(mode="json"),
            )
            if self.log:
                self.log.append("harness_request", request=request.model_dump(mode="json"))
            step = self.harness.select(request)
            if self.log:
                self.log.append("assistant_step", step=step.model_dump(mode="json"))
            if step.ask_user is not None:
                return TurnResult(ask_user=step.ask_user, tool_results=results)
            if step.answer is not None:
                accepted, unsupported = check_answer(step.answer, sources)
                if self.log:
                    self.log.append("checker", accepted=accepted, unsupported=unsupported)
                if accepted:
                    return TurnResult(answer=step.answer, tool_results=results)
                return TurnResult(
                    answer="I can only report values returned by NX tools.", tool_results=results
                )
            for call in step.tool_calls:
                call_key = json.dumps(
                    {"tool": call.tool, "args": call.args}, sort_keys=True, separators=(",", ":")
                )
                if call_key in issued_calls:
                    return TurnResult(
                        ask_user=(
                            f"The assistant repeated the NX tool '{call.tool}' without new input. "
                            "Please retry the request."
                        ),
                        tool_results=results,
                    )
                semantic_key = _semantic_call_key(call.tool, call.args)
                if semantic_key in failed_calls:
                    return TurnResult(
                        ask_user=(
                            f"The assistant repeated failed NX tool '{call.tool}' "
                            "without changing the target. Please retry the request."
                        ),
                        tool_results=results,
                    )
                try:
                    outcome = self.registry.execute(call.tool, call.args)
                except ToolError as exc:
                    return TurnResult(ask_user=str(exc), tool_results=results)
                if outcome.needs_confirmation:
                    if confirm is None:
                        return TurnResult(ask_user=outcome.preview, tool_results=results)
                    if not confirm(outcome.preview or "Confirm operation?"):
                        return TurnResult(ask_user="Operation cancelled.", tool_results=results)
                    outcome = self.registry.execute(call.tool, call.args, confirmed=True)
                if not outcome.ok:
                    message = outcome.error or f"NX tool '{call.tool}' failed."
                    failed_calls.add(semantic_key)
                    return TurnResult(ask_user=message, tool_results=results)
                issued_calls.add(call_key)
                results.append(outcome.model_dump(mode="json"))
                if _has_measurement_failure(outcome.result):
                    failed_calls.add(semantic_key)
                sources.append(outcome.result or {})
                self.conversation.append(
                    {
                        "role": "tool",
                        "content": json.dumps(outcome.model_dump(mode="json"), sort_keys=True),
                    }
                )
                if self.log:
                    self.log.append(
                        "tool_result", tool=call.tool, result=outcome.model_dump(mode="json")
                    )


def _semantic_call_key(tool: str, args: dict[str, Any]) -> str:
    """Normalize only failed measurement IDs for fallback-loop detection."""

    if tool == "measure" and isinstance(args.get("requests"), list):
        normalized = []
        for request in args["requests"]:
            if isinstance(request, dict):
                normalized.append(
                    {
                        "kind": request.get("kind"),
                        "a": request.get("a"),
                        "b": request.get("b"),
                    }
                )
        args = {"requests": normalized}
    return json.dumps({"tool": tool, "args": args}, sort_keys=True, separators=(",", ":"))


def _has_measurement_failure(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    measurements = result.get("results")
    if not isinstance(measurements, list) or not measurements:
        return isinstance(measurements, list)
    return any(
        isinstance(item, dict) and (item.get("error") or item.get("value") is None)
        for item in measurements
    )
