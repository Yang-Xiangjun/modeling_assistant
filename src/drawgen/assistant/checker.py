"""Number provenance checks (HANDOFF 17.5, NFR-12).

Answers: every number in the answer must match a number from the sources at
the precision the answer shows (``12.35`` matches ``12.3456``). The length of a
list in a tool result counts as a source number, so "2 faces" can be checked.
Digits inside identifiers (handles, tags, IDs, paths) are never sources.

Tool arguments: every numeric argument the model puts into a session or change
tool must appear, exactly, in a user message or a prior tool result.
"""

from __future__ import annotations

import contextlib
import re
from typing import Any

# A letter right before digits marks a unit or name ("mm2", "M6"), except "x" as in "100x60".
NUMBER = re.compile(r"(?<![A-WYZa-wyz0-9_.:])[-+]?\d+(?:[.,]\d+)?")

# Keys whose values identify objects rather than measure them.
_IDENTIFIER_KEYS = frozenset(
    {"handle", "tag", "id", "guid", "path", "undo_mark", "token", "signature", "asset_id"}
)


def _tokens(text: str) -> list[tuple[float, int]]:
    """Numbers in prose with the count of decimals shown."""

    out: list[tuple[float, int]] = []
    for token in NUMBER.findall(text):
        normalized = token.replace(",", ".")
        decimals = len(normalized.split(".", 1)[1]) if "." in normalized else 0
        with contextlib.suppress(ValueError):
            out.append((float(normalized), decimals))
    return out


def _numbers(value: Any) -> list[float]:
    """Numbers a source vouches for, including list lengths as counts."""

    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        return [number for number, _ in _tokens(value)]
    if isinstance(value, dict):
        return [
            n
            for key, item in value.items()
            if str(key).lower() not in _IDENTIFIER_KEYS
            for n in _numbers(item)
        ]
    if isinstance(value, (list, tuple)):
        return [float(len(value)), *(n for item in value for n in _numbers(item))]
    return []


def check_answer(
    answer: str, sources: list[Any], tolerance: float = 1e-9
) -> tuple[bool, list[float]]:
    """Return (accepted, unsupported numbers) for an answer."""

    allowed = [n for source in sources for n in _numbers(source)]
    unsupported: list[float] = []
    for number, decimals in _tokens(answer):
        half_step = 0.5 * 10.0**-decimals
        if not any(abs(number - candidate) <= half_step + tolerance for candidate in allowed):
            unsupported.append(number)
    return not unsupported, unsupported


def _argument_numbers(value: Any) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        return [n for item in value.values() for n in _argument_numbers(item)]
    if isinstance(value, (list, tuple)):
        return [n for item in value for n in _argument_numbers(item)]
    return []


def ungrounded_arguments(
    args: dict[str, Any], sources: list[Any], tolerance: float = 1e-9
) -> list[float]:
    """Numeric arguments that appear in no source (empty list means grounded)."""

    allowed = [n for source in sources for n in _numbers(source)]
    return [
        number
        for number in _argument_numbers(args)
        if not any(abs(number - candidate) <= tolerance for candidate in allowed)
    ]
