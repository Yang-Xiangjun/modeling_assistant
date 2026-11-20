"""Local JSONL session log."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


class SessionLog:
    def __init__(self, root: Path = Path("runs/assistant"), session_id: str | None = None) -> None:
        self.session_id = session_id or uuid.uuid4().hex
        self.path = root / self.session_id / "events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: str, **payload: Any) -> None:
        record = {"ts": time.time(), "event": event, **payload}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
