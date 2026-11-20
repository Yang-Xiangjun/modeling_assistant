"""Long-lived assistant sessions for a panel that talks over HTTP.

One ``AssistantSession`` owns one ``AssistantAgent`` for the whole conversation,
so clarification and history survive between messages. A turn runs on a worker
thread. When a change tool needs confirmation, the turn pauses on that exact
tool call and exposes its preview; only ``resolve_confirmation`` with the
matching confirmation ID lets it continue (rule 8, HANDOFF 17.6). The panel
holds no logic: it renders turn snapshots and forwards the user's click.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from drawgen.assistant.agent import AssistantAgent

TurnStatus = Literal["running", "needs_confirmation", "done", "error"]

_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class SessionError(Exception):
    """A session or turn request is not valid in the current state."""


@dataclass
class _Turn:
    id: str
    message: str
    status: TurnStatus = "running"
    confirm_id: str | None = None
    preview: str | None = None
    answer: str | None = None
    ask_user: str | None = None
    error: str | None = None
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    decision: threading.Event = field(default_factory=threading.Event)
    approved: bool = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "turn_id": self.id,
            "status": self.status,
            "confirm_id": self.confirm_id,
            "preview": self.preview,
            "answer": self.answer,
            "ask_user": self.ask_user,
            "error": self.error,
            "tool_results": self.tool_results,
        }


class AssistantSession:
    """One conversation: one agent, at most one running turn."""

    def __init__(self, agent: AssistantAgent, *, confirm_timeout_s: float = 600.0) -> None:
        self.agent = agent
        self.confirm_timeout_s = confirm_timeout_s
        self._lock = threading.Lock()
        self._turns: dict[str, _Turn] = {}
        self._active: str | None = None

    def start_turn(self, message: str) -> str:
        text = message.strip()
        if not text:
            raise SessionError("message is empty")
        with self._lock:
            if self._active is not None:
                raise SessionError("a turn is already running in this session")
            turn = _Turn(id=uuid.uuid4().hex, message=text)
            self._turns[turn.id] = turn
            self._active = turn.id
        threading.Thread(target=self._run, args=(turn,), daemon=True).start()
        return turn.id

    def get_turn(self, turn_id: str) -> dict[str, Any]:
        with self._lock:
            return self._turn(turn_id).snapshot()

    def resolve_confirmation(self, turn_id: str, confirm_id: str, approve: bool) -> None:
        with self._lock:
            turn = self._turn(turn_id)
            if turn.status != "needs_confirmation" or turn.confirm_id != confirm_id:
                raise SessionError("no pending confirmation with this ID")
            turn.approved = approve
            turn.status = "running"
            turn.confirm_id = None
            turn.decision.set()

    def wait(self, turn_id: str, timeout_s: float = 5.0) -> dict[str, Any]:
        """Block until the turn leaves ``running`` (for tests and simple clients)."""

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            snapshot = self.get_turn(turn_id)
            if snapshot["status"] != "running":
                return snapshot
            time.sleep(0.01)
        return self.get_turn(turn_id)

    def _turn(self, turn_id: str) -> _Turn:
        turn = self._turns.get(turn_id)
        if turn is None:
            raise SessionError("unknown turn")
        return turn

    def _confirm(self, turn: _Turn) -> Callable[[str], bool]:
        def confirm(preview: str) -> bool:
            with self._lock:
                turn.decision.clear()
                turn.approved = False
                turn.preview = preview
                turn.confirm_id = uuid.uuid4().hex
                turn.status = "needs_confirmation"
            decided = turn.decision.wait(self.confirm_timeout_s)
            with self._lock:
                if not decided:
                    turn.status = "running"
                    turn.confirm_id = None
                return decided and turn.approved

        return confirm

    def _run(self, turn: _Turn) -> None:
        try:
            result = self.agent.run(turn.message, confirm=self._confirm(turn))
        except Exception as exc:  # the panel must stay usable after a failed turn
            with self._lock:
                turn.status = "error"
                turn.error = str(exc)
                self._active = None
            return
        with self._lock:
            turn.answer = result.answer
            turn.ask_user = result.ask_user
            turn.tool_results = [item.model_dump(mode="json") for item in result.tool_results]
            turn.status = "done"
            self._active = None


class SessionManager:
    """Creates sessions on first use from a factory keyed by session ID."""

    def __init__(
        self,
        agent_factory: Callable[[str], AssistantAgent],
        *,
        confirm_timeout_s: float = 600.0,
    ) -> None:
        self._factory = agent_factory
        self._confirm_timeout_s = confirm_timeout_s
        self._lock = threading.Lock()
        self._sessions: dict[str, AssistantSession] = {}

    def get(self, session_id: str) -> AssistantSession:
        if not _SESSION_ID.match(session_id):
            raise SessionError("invalid session ID")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = AssistantSession(
                    self._factory(session_id), confirm_timeout_s=self._confirm_timeout_s
                )
                self._sessions[session_id] = session
            return session
