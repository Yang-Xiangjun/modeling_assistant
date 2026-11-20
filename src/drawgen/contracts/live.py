"""Typed contracts for the interactive NX bridge and assistant MVP."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from drawgen.contracts.common import Contract, Fingerprint
from drawgen.contracts.worker import WorkerStatus


class BridgeRequest(Contract):
    protocol: Literal["1"] = "1"
    id: str
    token: str
    command: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class BridgeResponse(Contract):
    id: str
    status: WorkerStatus
    result: dict[str, Any] | None = None


class PartRef(Contract):
    name: str
    path: str | None = None
    modified: bool | None = None


class SessionContext(Contract):
    schema_: Literal["session_context/0"] = Field("session_context/0", alias="schema")
    work_part: PartRef | None = None
    displayed_part: PartRef | None = None
    application: str | None = None
    active_sheet: str | None = None
    active_view: str | None = None


EntityKind = Literal[
    "face",
    "edge",
    "body",
    "component",
    "feature",
    "dimension",
    "view",
    "note",
    "other",
]


class SelectedObject(Contract):
    handle: str
    entity_kind: EntityKind
    object_type: str
    component_path: str | None = None
    fingerprint: Fingerprint | None = None
    properties: dict[str, float | str | bool] = Field(default_factory=dict)


class Selection(Contract):
    schema_: Literal["selection/0"] = Field("selection/0", alias="schema")
    items: list[SelectedObject] = Field(default_factory=list)


MeasureKind = Literal["area", "volume", "length", "radius", "diameter", "distance", "angle"]


class LiveMeasureRequest(Contract):
    id: str
    kind: MeasureKind
    a: str
    b: str | None = None


class LiveMeasureResult(Contract):
    id: str
    value: float | None = None
    unit: Literal["mm", "mm2", "mm3", "deg"] | None = None
    error: str | None = None


class LiveMeasureResults(Contract):
    results: list[LiveMeasureResult] = Field(default_factory=list)


ListKind = Literal[
    "attributes",
    "expressions",
    "features",
    "components",
    "sheets",
    "views",
    "dimensions",
]


class ListRequest(Contract):
    what: ListKind
    of: str | None = None


class ListResult(Contract):
    items: list[dict[str, Any]] = Field(default_factory=list)


class OperationResult(Contract):
    command: str
    undo_mark: str | None = None
    changed: bool = False
    saved: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
