"""Command line entry point: `drawgen <command>`."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from drawgen import __version__
from drawgen.assistant.agent import AssistantAgent
from drawgen.assistant.harness import (
    CodexApiHarness,
    FakeHarness,
    HarnessAdapter,
    HarnessError,
    PiAgentHarness,
)
from drawgen.assistant.log import SessionLog
from drawgen.backends import get_backend
from drawgen.backends.base import BackendError
from drawgen.backends.bridge import BridgeBackend
from drawgen.backends.live import LiveBackend, LiveBackendError
from drawgen.backends.live_mock import MockLiveBackend
from drawgen.contracts.live import LiveMeasureResult, SelectedObject, Selection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drawgen", description="AI drawing harness")
    parser.add_argument("--version", action="version", version=f"drawgen {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    ping = subparsers.add_parser("ping", help="check CAD backend availability")
    ping.add_argument("--backend", choices=("mock", "nx"), default="mock")
    ping.add_argument("--run-journal", type=Path)
    ping.add_argument("--timeout", type=float, default=600.0)
    ping.add_argument("--fixtures", type=Path)
    live = subparsers.add_parser("live", help="query the interactive NX bridge")
    live_sub = live.add_subparsers(dest="live_command")
    live_ping = live_sub.add_parser("ping", help="ping the live bridge")
    live_ping.add_argument("--backend", choices=("mock", "bridge"), default="mock")
    live_ping.add_argument("--endpoint", type=Path)
    live_selection = live_sub.add_parser("selection", help="read the live selection")
    live_selection.add_argument("--backend", choices=("mock", "bridge"), default="mock")
    live_selection.add_argument("--endpoint", type=Path)
    live_selection.add_argument("--no-properties", action="store_true")
    assistant = subparsers.add_parser("assistant", help="run the chat assistant")
    assistant_sub = assistant.add_subparsers(dest="assistant_command")
    chat = assistant_sub.add_parser("chat", help="chat with the live backend")
    chat.add_argument("--backend", choices=("mock", "bridge"), default="mock")
    chat.add_argument("--endpoint", type=Path)
    chat.add_argument("--harness", choices=("fake", "codex", "pi"), default="pi")
    chat.add_argument("--message", help="run one message and exit")
    chat.add_argument("--session", help="session log identifier")
    chat.add_argument(
        "--yes",
        action="store_true",
        help="confirm change tools automatically for a trusted local UI request",
    )
    panel = assistant_sub.add_parser("panel", help="open the Tkinter chat window")
    panel.add_argument("--backend", choices=("mock", "bridge"), default="mock")
    panel.add_argument("--endpoint", type=Path)
    panel.add_argument("--harness", choices=("fake", "codex", "pi"), default="pi")
    panel.add_argument("--session", help="session log identifier")
    return parser


def live_backend(name: str, endpoint: Path | None) -> LiveBackend:
    if name == "mock":
        return MockLiveBackend(
            selection=Selection(
                items=[
                    SelectedObject(
                        handle="demo-face",
                        entity_kind="face",
                        object_type="Face",
                        properties={"area": 12.5},
                    )
                ]
            ),
            measurements={
                "m0": LiveMeasureResult(id="m0", value=12.5, unit="mm2"),
                "v0": LiveMeasureResult(id="v0", value=120000.0, unit="mm3"),
            },
        )
    if endpoint is None:
        raise ValueError("--endpoint is required for the bridge backend")
    return BridgeBackend(endpoint)


def harness_for(name: str) -> HarnessAdapter:
    if name == "fake":
        return FakeHarness()
    if name == "codex":
        return CodexApiHarness()
    return PiAgentHarness()


def _run_chat(args: argparse.Namespace) -> int:
    backend = live_backend(args.backend, args.endpoint)
    harness = harness_for(args.harness)
    agent = AssistantAgent(backend, harness, log=SessionLog(session_id=args.session))

    def confirm(preview: str) -> bool:
        if args.yes:
            return True
        try:
            answer = input(f"{preview}\nConfirm [y/N]? ").strip().lower()
        except EOFError:
            return False
        return answer in {"y", "yes"}

    def one(message: str) -> None:
        result = agent.run(message, confirm=confirm)
        if result.answer:
            print(result.answer)
        if result.ask_user:
            print(result.ask_user)

    if args.message:
        try:
            one(args.message)
        except HarnessError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    print("drawgen assistant; type 'exit' to quit")
    while True:
        try:
            message = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.strip().lower() in {"exit", "quit"}:
            break
        if message.strip():
            try:
                one(message)
            except HarnessError as exc:
                print(str(exc), file=sys.stderr)
    return 0


def _run_panel(args: argparse.Namespace) -> int:
    from drawgen.assistant.panel.app import run_panel

    backend = live_backend(args.backend, args.endpoint)
    harness = harness_for(args.harness)
    run_panel(backend, harness, log=SessionLog(session_id=args.session))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "ping":
        kwargs: dict[str, object] = {}
        if args.backend == "mock":
            kwargs["fixture_root"] = args.fixtures
        else:
            if args.run_journal is not None:
                kwargs["run_journal"] = args.run_journal
            kwargs["timeout_s"] = args.timeout
        try:
            result = get_backend(args.backend, **kwargs).ping()
        except BackendError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
    elif args.command == "live":
        if args.live_command is None:
            parser.parse_args(["live", "--help"])
        try:
            backend = live_backend(args.backend, args.endpoint)
            if args.live_command == "ping":
                result = backend.ping()
            else:
                result = backend.get_selection(not args.no_properties).model_dump(mode="json")
        except (BackendError, LiveBackendError, ValueError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
    elif args.command == "assistant":
        if args.assistant_command == "panel":
            return _run_panel(args)
        if args.assistant_command != "chat":
            parser.parse_args(["assistant", "--help"])
        return _run_chat(args)
    return 0
