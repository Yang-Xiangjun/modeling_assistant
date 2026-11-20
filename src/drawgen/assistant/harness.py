"""Harness adapters: fake, OpenAI Responses/Codex API, and pi JSON mode."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from drawgen.assistant.contracts import AssistantStep, HarnessRequest


class HarnessError(Exception):
    """A harness could not produce a valid assistant step."""


class HarnessAdapter(Protocol):
    def select(self, request: HarnessRequest) -> AssistantStep: ...


def _system_prompt() -> str:
    return (
        "You are a constrained CAD assistant. Return JSON only, matching the supplied "
        "AssistantStep schema. You may call only the listed tools. Never write code, "
        "NXOpen, shell commands, or invented measurements. For a requested operation, "
        "follow the supplied operation_plan. Use search_nx_api before selecting an "
        "unfamiliar NX operation, search the plan's API query synonyms, and use only "
        "typed tools supported by the returned evidence. If a candidate fails, use a "
        "different validated candidate or ask for clarification. "
        "emit a tool call even when it changes NX. The caller handles confirmation, "
        "so do not use ask_user for confirmation. Use ask_user only when required "
        "information is missing or ambiguous. After a tool returns a successful "
        "result for the current request, return a concise answer that summarizes "
        "the result. Do not repeat the same successful tool call. For immediate "
        "view operations such as fit_view and orient_view, always answer after "
        "the first successful tool result. If a tool result contains an error or "
        "a measurement with no value, first use search_nx_api or another validated "
        "candidate from the operation plan when one exists. Report the failure "
        "when no fallback remains. For surface area, read the "
        "selection first, then use measure with kind area on the selected face, "
        "body, or body-feature handle. For volume, read the selection first, then "
        "use measure with kind volume on the selected body or body-feature handle. "
        "For box creation, map an explicitly "
        "requested hole distance from the left or bottom boundary to "
        "hole_center_left and hole_center_bottom in millimetres. Do not repeat "
        "the same typed call after it fails."
    )


def _parse_step(value: Any) -> AssistantStep:
    if isinstance(value, dict):
        if "assistant_step" in value:
            return _parse_step(value["assistant_step"])
        if "step" in value:
            return _parse_step(value["step"])
        try:
            return AssistantStep.model_validate(value)
        except Exception:
            pass
        message = value.get("message") if isinstance(value.get("message"), dict) else value
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return _parse_text_step(content)
            if isinstance(content, list):
                text = "".join(
                    str(item.get("text", "")) for item in content if isinstance(item, dict)
                )
                if text:
                    return _parse_text_step(text)
        messages = value.get("messages")
        if isinstance(messages, list):
            for item in reversed(messages):
                try:
                    return _parse_step(item)
                except HarnessError:
                    continue
        event = value.get("assistantMessageEvent")
        if isinstance(event, dict) and isinstance(event.get("content"), str):
            return _parse_text_step(event["content"])
    if isinstance(value, str):
        return _parse_text_step(value)
    raise HarnessError("harness did not return an AssistantStep")


def _parse_text_step(text: str) -> AssistantStep:
    candidate = text.strip()
    if "```" in candidate:
        candidate = candidate.replace("```json", "").replace("```", "").strip()
    try:
        return AssistantStep.model_validate_json(candidate)
    except Exception as exc:
        raise HarnessError("harness returned non-JSON assistant output") from exc


class FakeHarness:
    """Deterministic scripted harness used by unit tests and offline demos."""

    def __init__(self, steps: Sequence[AssistantStep] | None = None) -> None:
        self.steps = list(steps or [])

    def select(self, request: HarnessRequest) -> AssistantStep:
        if self.steps:
            return self.steps.pop(0)
        user = next(
            (
                item["content"].lower()
                for item in reversed(request.conversation)
                if item["role"] == "user"
            ),
            "",
        )
        if "selection" in user:
            if not request.tool_results:
                return AssistantStep(tool_calls=[{"tool": "get_selection", "args": {}}])
            return AssistantStep(answer="NX returned the current selection.")
        if "area" in user or "surface" in user:
            if not request.tool_results:
                return AssistantStep(tool_calls=[{"tool": "get_selection", "args": {}}])
            selection = request.tool_results[0].get("result", {})
            items = selection.get("items", []) if isinstance(selection, dict) else []
            if items:
                handle = items[0].get("handle")
                if handle and len(request.tool_results) == 1:
                    return AssistantStep(
                        tool_calls=[
                            {
                                "tool": "measure",
                                "args": {"requests": [{"id": "m0", "kind": "area", "a": handle}]},
                            }
                        ]
                    )
            for item in reversed(request.tool_results):
                result = item.get("result", {})
                if isinstance(result, dict) and result.get("results"):
                    error = result["results"][0].get("error")
                    if error:
                        return AssistantStep(ask_user=f"NX measurement failed: {error}")
                if isinstance(result, dict) and result.get("results"):
                    value = result["results"][0].get("value")
                    if value is not None:
                        return AssistantStep(answer=f"The measured surface area is {value} mm2.")
            return AssistantStep(answer="NX did not return a surface-area measurement.")
        if "volume" in user:
            if not request.tool_results:
                return AssistantStep(tool_calls=[{"tool": "get_selection", "args": {}}])
            selection = request.tool_results[0].get("result", {})
            items = selection.get("items", []) if isinstance(selection, dict) else []
            if items:
                handle = items[0].get("handle")
                if handle and len(request.tool_results) == 1:
                    return AssistantStep(
                        tool_calls=[
                            {
                                "tool": "measure",
                                "args": {"requests": [{"id": "v0", "kind": "volume", "a": handle}]},
                            }
                        ]
                    )
            for item in reversed(request.tool_results):
                result = item.get("result", {})
                if isinstance(result, dict) and result.get("results"):
                    error = result["results"][0].get("error")
                    if error:
                        return AssistantStep(ask_user=f"NX measurement failed: {error}")
                if isinstance(result, dict) and result.get("results"):
                    value = result["results"][0].get("value")
                    if value is not None:
                        return AssistantStep(answer=f"The measured volume is {value} mm3.")
            return AssistantStep(answer="NX did not return a volume measurement.")
        if any(word in user for word in ("show", "hide", "isolate")):
            if not request.tool_results:
                return AssistantStep(tool_calls=[{"tool": "get_selection", "args": {}}])
            selection = request.tool_results[0].get("result", {})
            items = selection.get("items", []) if isinstance(selection, dict) else []
            if items:
                handle = items[0].get("handle")
                operation = next(word for word in ("show", "hide", "isolate") if word in user)
                return AssistantStep(
                    tool_calls=[{"tool": f"{operation}_entity", "args": {"handle": handle}}]
                )
            return AssistantStep(ask_user="Select an entity before changing its display state.")
        if "fit" in user:
            return AssistantStep(tool_calls=[{"tool": "fit_view", "args": {}}])
        if any(word in user for word in ("box", "through-hole", "through hole", "solid")):
            if request.tool_results:
                return AssistantStep(
                    answer="Created the requested box with a centered through-hole in NX."
                )
            return AssistantStep(
                tool_calls=[
                    {
                        "tool": "create_box_with_hole",
                        "args": {
                            "width": 100.0,
                            "depth": 60.0,
                            "height": 20.0,
                            "hole_diameter": 10.0,
                        },
                    }
                ]
            )
        return AssistantStep(ask_user="Select an entity or ask for its area/selection.")


class CodexApiHarness:
    """OpenAI Responses API adapter using structured JSON output.

    The API key is read from OPENAI_API_KEY. The default model can be changed with
    DRAWGEN_CODEX_MODEL; no secret is stored in the repository.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.api_key = (
            api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("CODEX_API_KEY")
        )
        self.model = model or os.environ.get("DRAWGEN_CODEX_MODEL", "gpt-5-codex")
        self.base_url = (
            base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")
        self.timeout_s = timeout_s

    def select(self, request: HarnessRequest) -> AssistantStep:
        if not self.api_key:
            raise HarnessError("OPENAI_API_KEY is not set")
        body = {
            "model": self.model,
            "input": [
                {
                    "role": "developer",
                    "content": [{"type": "input_text", "text": _system_prompt()}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": request.model_dump_json()}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "assistant_step",
                    "strict": True,
                    "schema": AssistantStep.model_json_schema(),
                }
            },
        }
        req = urllib.request.Request(
            f"{self.base_url}/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise HarnessError(f"Codex API request failed: {exc}") from exc
        output_text = payload.get("output_text")
        if isinstance(output_text, str):
            return _parse_text_step(output_text)
        for item in payload.get("output", []):
            if isinstance(item, dict):
                try:
                    return _parse_step(item)
                except HarnessError:
                    continue
        raise HarnessError("Codex API response contained no assistant step")


class PiAgentHarness:
    """Adapter for pi's non-interactive JSON mode.

    Override DRAWGEN_PI_COMMAND and DRAWGEN_PI_ARGS when the installed pi
    distribution uses a different executable or flags. DRAWGEN_PI_SKILL can
    point to an additional skill file loaded for every Branch C turn.
    """

    def __init__(
        self, *, command: str | None = None, args: str | None = None, timeout_s: float = 60.0
    ) -> None:
        self.command = command or os.environ.get("DRAWGEN_PI_COMMAND", "pi")
        configured = args or os.environ.get("DRAWGEN_PI_ARGS", "--print --mode json")
        self.args = shlex.split(configured, posix=False)
        default_skill = (
            Path(__file__).resolve().parents[3] / ".pi-agent" / "skills" / "nxopen-cad" / "SKILL.md"
        )
        skill = os.environ.get("DRAWGEN_PI_SKILL", str(default_skill))
        if skill and Path(skill).is_file():
            self.args.extend(["--skill", skill])
        self.timeout_s = timeout_s

    def select(self, request: HarnessRequest) -> AssistantStep:
        schema = json.dumps(AssistantStep.model_json_schema(), separators=(",", ":"))
        prompt = (
            f"{_system_prompt()}\nAssistantStep JSON Schema:\n{schema}\n"
            "Return exactly one JSON object matching that schema for this request:\n"
            f"{request.model_dump_json()}"
        )
        command = self.command
        command_path = shutil.which(command) or command
        if os.name == "nt" and Path(command_path).suffix.lower() in {".cmd", ".bat"}:
            invocation = ["cmd.exe", "/d", "/c", command_path, *self.args]
        else:
            invocation = [command_path, *self.args]
        try:
            completed = subprocess.run(
                invocation,
                input=prompt,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=self.timeout_s,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HarnessError(f"pi-agent invocation failed: {exc}") from exc
        if completed.returncode != 0:
            raise HarnessError(
                f"pi-agent exited with {completed.returncode}: {completed.stderr[-1000:]}"
            )
        stdout = completed.stdout or ""
        lines = [line for line in stdout.splitlines() if line.strip()]
        for line in reversed(lines):
            try:
                return _parse_step(json.loads(line))
            except (json.JSONDecodeError, HarnessError):
                continue
        return _parse_text_step(stdout)
