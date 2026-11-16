"""Plain-Python command used to exercise the worker protocol."""

from typing import Any


def run(inputs: dict[str, Any], options: dict[str, Any], log: list[str]) -> dict[str, Any]:
    if options.get("fail"):
        raise ValueError("selftest requested to fail")
    log.append("selftest command ran")
    return {"echo": inputs}
