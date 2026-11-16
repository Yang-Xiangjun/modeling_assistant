"""Deterministic JSON serialization and SHA-256 helpers."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical_json(obj: Any) -> str:
    """Serialize an object as compact, deterministic, UTF-8-friendly JSON."""

    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_canonical(obj: Any) -> str:
    """Return the hexadecimal SHA-256 digest of :func:`canonical_json`."""

    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def read_json(path: str | os.PathLike[str]) -> Any:
    """Read and decode a UTF-8 JSON file."""

    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: str | os.PathLike[str], obj: Any) -> None:
    """Write indented, sorted UTF-8 JSON with a trailing newline."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        json.dump(
            obj,
            stream,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        stream.write("\n")
