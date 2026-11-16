"""Command line entry point: `drawgen <command>`."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from drawgen import __version__
from drawgen.backends import get_backend
from drawgen.backends.base import BackendError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drawgen", description="AI drawing harness")
    parser.add_argument("--version", action="version", version=f"drawgen {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    ping = subparsers.add_parser("ping", help="check CAD backend availability")
    ping.add_argument("--backend", choices=("mock", "nx"), default="mock")
    ping.add_argument("--run-journal", type=Path)
    ping.add_argument("--timeout", type=float, default=600.0)
    ping.add_argument("--fixtures", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
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
    return 0
