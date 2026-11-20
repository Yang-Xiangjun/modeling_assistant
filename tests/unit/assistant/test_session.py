"""Panel sessions: confirmation binds to the paused call, state survives turns."""

from __future__ import annotations

import pytest

from drawgen.assistant.agent import AssistantAgent
from drawgen.assistant.contracts import AssistantStep
from drawgen.assistant.harness import FakeHarness
from drawgen.assistant.session import AssistantSession, SessionError, SessionManager
from drawgen.backends.live_mock import MockLiveBackend


def _show_session(backend: MockLiveBackend) -> AssistantSession:
    harness = FakeHarness(
        [
            AssistantStep(tool_calls=[{"tool": "show_entity", "args": {"handle": "h1"}}]),
            AssistantStep(answer="Shown."),
        ]
    )
    return AssistantSession(AssistantAgent(backend, harness))


def test_change_waits_for_confirmation_and_runs_only_after_approval() -> None:
    backend = MockLiveBackend()
    session = _show_session(backend)
    turn_id = session.start_turn("Show this entity")

    paused = session.wait(turn_id)
    assert paused["status"] == "needs_confirmation"
    assert "show_entity" in paused["preview"]
    assert backend.executed == []

    session.resolve_confirmation(turn_id, paused["confirm_id"], approve=True)
    done = session.wait(turn_id)
    assert done["status"] == "done"
    assert done["answer"] == "Shown."
    assert backend.executed == [("show_entity", {"handle": "h1"})]


def test_cancel_leaves_nx_unchanged() -> None:
    backend = MockLiveBackend()
    session = _show_session(backend)
    turn_id = session.start_turn("Show this entity")
    paused = session.wait(turn_id)

    session.resolve_confirmation(turn_id, paused["confirm_id"], approve=False)
    done = session.wait(turn_id)
    assert done["ask_user"] == "Operation cancelled."
    assert backend.executed == []


def test_wrong_confirmation_id_is_rejected() -> None:
    backend = MockLiveBackend()
    session = _show_session(backend)
    turn_id = session.start_turn("Show this entity")
    session.wait(turn_id)

    with pytest.raises(SessionError):
        session.resolve_confirmation(turn_id, "not-the-id", approve=True)
    assert backend.executed == []


def test_confirmation_timeout_cancels() -> None:
    backend = MockLiveBackend()
    harness = FakeHarness(
        [AssistantStep(tool_calls=[{"tool": "show_entity", "args": {"handle": "h1"}}])]
    )
    session = AssistantSession(AssistantAgent(backend, harness), confirm_timeout_s=0.05)
    turn_id = session.start_turn("Show this entity")
    done = session.wait(turn_id, timeout_s=2.0)
    while done["status"] != "done":
        done = session.wait(turn_id, timeout_s=2.0)
    assert done["ask_user"] == "Operation cancelled."
    assert backend.executed == []


def test_one_turn_at_a_time_and_history_is_kept() -> None:
    backend = MockLiveBackend()
    session = _show_session(backend)
    turn_id = session.start_turn("Show this entity")
    with pytest.raises(SessionError):
        session.start_turn("Another message")
    paused = session.wait(turn_id)
    session.resolve_confirmation(turn_id, paused["confirm_id"], approve=False)
    session.wait(turn_id)

    user_messages = [m for m in session.agent.conversation if m["role"] == "user"]
    assert [m["content"] for m in user_messages] == ["Show this entity"]


def test_manager_reuses_sessions_and_validates_ids() -> None:
    created: list[str] = []

    def factory(session_id: str) -> AssistantAgent:
        created.append(session_id)
        return AssistantAgent(MockLiveBackend(), FakeHarness())

    manager = SessionManager(factory)
    first = manager.get("session-0001")
    assert manager.get("session-0001") is first
    assert created == ["session-0001"]
    with pytest.raises(SessionError):
        manager.get("../etc")
