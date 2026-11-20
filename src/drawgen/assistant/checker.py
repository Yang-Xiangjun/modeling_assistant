"""Reject answer numbers that did not come from the current tool results."""

from __future__ import annotations

import contextlib
import re
from typing import Any

NUMBER = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:[.,]\d+)?")


def _numbers(value: Any) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        out: list[float] = []
        for token in NUMBER.findall(value):
            with contextlib.suppress(ValueError):
                out.append(float(token.replace(",", ".")))
        return out
    if isinstance(value, dict):
        return [n for item in value.values() for n in _numbers(item)]
    if isinstance(value, (list, tuple)):
        return [n for item in value for n in _numbers(item)]
    return []


def check_answer(
    answer: str, sources: list[Any], tolerance: float = 1e-9
) -> tuple[bool, list[float]]:
    allowed = _numbers(sources)
    unsupported: list[float] = []
    for number in _numbers(answer):
        if not any(abs(number - candidate) <= tolerance for candidate in allowed):
            unsupported.append(number)
    return not unsupported, unsupported
