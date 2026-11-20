"""Typed, closed tool registry for the live assistant."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from drawgen.assistant.api_search import search_nx_api
from drawgen.assistant.contracts import ToolExecution, ToolSpec
from drawgen.backends.live import LiveBackend
from drawgen.contracts.live import ListRequest, LiveMeasureRequest
from drawgen.contracts.operation_plan import CandidateKind


class EmptyArgs(BaseModel):
    model_config = {"extra": "forbid"}


class SelectionArgs(BaseModel):
    include_properties: bool = True
    model_config = {"extra": "forbid"}


class MeasureArgs(BaseModel):
    requests: list[LiveMeasureRequest] = Field(default_factory=list)
    model_config = {"extra": "forbid"}


class ApiSearchArgs(BaseModel):
    query: str = Field(min_length=1)
    kind: CandidateKind | None = None
    namespace: str | None = None
    limit: int = Field(default=8, ge=1, le=20)
    model_config = {"extra": "forbid"}


class ListArgs(ListRequest):
    pass


class HandleArgs(BaseModel):
    handle: str
    model_config = {"extra": "forbid"}


class PathArgs(BaseModel):
    path: str
    model_config = {"extra": "forbid"}


class AttributeArgs(BaseModel):
    handle: str
    title: str
    value: str
    model_config = {"extra": "forbid"}


class ExpressionArgs(BaseModel):
    handle: str
    value: float | str
    model_config = {"extra": "forbid"}


class ScopeArgs(BaseModel):
    scope: str = "work_part"
    model_config = {"extra": "forbid"}


class CreateBoxWithHoleArgs(BaseModel):
    width: float = Field(default=100.0, gt=0.0, description="Box width in millimetres.")
    depth: float = Field(default=60.0, gt=0.0, description="Box depth in millimetres.")
    height: float = Field(default=20.0, gt=0.0, description="Box height in millimetres.")
    hole_diameter: float = Field(
        default=10.0, gt=0.0, description="Through-hole diameter in millimetres."
    )
    hole_center_left: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Hole-center distance from the box left boundary in millimetres. "
            "Defaults to the box center."
        ),
    )
    hole_center_bottom: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Hole-center distance from the box bottom boundary in millimetres. "
            "Defaults to the box center."
        ),
    )
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_dimensions(self) -> CreateBoxWithHoleArgs:
        if self.hole_diameter >= min(self.width, self.depth):
            raise ValueError("hole_diameter must be smaller than both box width and depth")
        radius = self.hole_diameter / 2.0
        if self.hole_center_left is not None and not (
            radius <= self.hole_center_left <= self.width - radius
        ):
            raise ValueError("hole_center_left must keep the hole inside the box width")
        if self.hole_center_bottom is not None and not (
            radius <= self.hole_center_bottom <= self.depth - radius
        ):
            raise ValueError("hole_center_bottom must keep the hole inside the box depth")
        return self


class CreateSheetArgs(BaseModel):
    template: str
    name: str = "SHT1"
    model_config = {"extra": "forbid"}


class BaseViewArgs(BaseModel):
    sheet_handle: str
    model_view: str
    scale: float = 1.0
    model_config = {"extra": "forbid"}


class ProjectedViewArgs(BaseModel):
    parent_handle: str
    direction: Literal["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
    model_config = {"extra": "forbid"}


class DimensionArgs(BaseModel):
    view_handle: str
    a: str
    b: str
    kind: Literal["linear", "diameter", "radius", "angular"] = "linear"
    model_config = {"extra": "forbid"}


class NoteArgs(BaseModel):
    view_handle: str
    text: str
    model_config = {"extra": "forbid"}


class ExportArgs(BaseModel):
    handle: str
    path: str
    model_config = {"extra": "forbid"}


@dataclass(frozen=True)
class ToolDefinition:
    spec: ToolSpec
    args_model: type[BaseModel]
    command: str | None = None
    handler: Callable[[LiveBackend, BaseModel], dict[str, Any]] | None = None
    # The bridge command this tool needs; None for tools that run locally.
    requires: str | None = None


class ToolError(Exception):
    """Tool name or argument validation failed."""


def _model_dump(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return value
    raise TypeError(f"tool result is not an object: {type(value).__name__}")


def _read_context(backend: LiveBackend, _: BaseModel) -> dict[str, Any]:
    return backend.get_context().model_dump(mode="json")


def _read_selection(backend: LiveBackend, args: BaseModel) -> dict[str, Any]:
    return backend.get_selection(bool(getattr(args, "include_properties", True))).model_dump(
        mode="json"
    )


def _read_measure(backend: LiveBackend, args: BaseModel) -> dict[str, Any]:
    typed = MeasureArgs.model_validate(args.model_dump())
    return backend.measure(typed.requests).model_dump(mode="json")


def _read_api_search(_: LiveBackend, args: BaseModel) -> dict[str, Any]:
    typed = ApiSearchArgs.model_validate(args.model_dump())
    candidates = search_nx_api(
        typed.query,
        kind=typed.kind,
        namespace=typed.namespace,
        limit=typed.limit,
    )
    return {
        "query": typed.query,
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
    }


def _read_list(backend: LiveBackend, args: BaseModel) -> dict[str, Any]:
    return backend.list(ListRequest.model_validate(args.model_dump())).model_dump(mode="json")


class ToolRegistry:
    def __init__(self, backend: LiveBackend) -> None:
        self.backend = backend
        self._tools: dict[str, ToolDefinition] = {}
        self._capabilities: frozenset[str] | None = None
        self._register_defaults()

    def _register(
        self,
        name: str,
        kind: str,
        description: str,
        args_model: type[BaseModel],
        *,
        command: str | None = None,
        handler: Callable[[LiveBackend, BaseModel], dict[str, Any]] | None = None,
        requires: str | None = None,
    ) -> None:
        self._tools[name] = ToolDefinition(
            ToolSpec(
                name=name,
                kind=kind,
                description=description,
                args_schema=args_model.model_json_schema(),
            ),
            args_model,
            command,
            handler,
            requires if requires is not None else command,
        )

    def _register_defaults(self) -> None:
        self._register(
            "get_context",
            "read",
            "Read the current NX session context.",
            EmptyArgs,
            handler=_read_context,
            requires="get_context",
        )
        self._register(
            "get_selection",
            "read",
            "Read the current NX selection.",
            SelectionArgs,
            handler=_read_selection,
            requires="get_selection",
        )
        self._register(
            "measure",
            "read",
            "Measure selected session handles.",
            MeasureArgs,
            handler=_read_measure,
            requires="measure",
        )
        self._register(
            "search_nx_api",
            "read",
            "Search the local NXOpen API catalog for validated planning candidates.",
            ApiSearchArgs,
            handler=_read_api_search,
        )
        self._register(
            "list",
            "read",
            "List typed objects from the current NX session.",
            ListArgs,
            handler=_read_list,
            requires="list",
        )
        for name, description, args_model, command, kind in (
            ("open_part", "Open a part by local path.", PathArgs, "open_part", "session"),
            (
                "switch_part",
                "Switch to a returned part handle.",
                HandleArgs,
                "switch_part",
                "session",
            ),
            ("orient_view", "Orient the active view.", EmptyArgs, "orient_view", "session"),
            ("fit_view", "Fit the active view.", EmptyArgs, "fit_view", "session"),
            (
                "create_box_with_hole",
                (
                    "Create a new NX part containing a box and a through-hole. "
                    "Dimensions and optional hole-center offsets are in millimetres."
                ),
                CreateBoxWithHoleArgs,
                "create_box_with_hole",
                "change",
            ),
            (
                "highlight_entity",
                "Highlight a returned entity handle.",
                HandleArgs,
                "highlight",
                "session",
            ),
            ("show_entity", "Show a returned entity handle.", HandleArgs, "show_entity", "change"),
            ("hide_entity", "Hide a returned entity handle.", HandleArgs, "hide_entity", "change"),
            (
                "isolate_entity",
                "Isolate a returned entity handle.",
                HandleArgs,
                "isolate_entity",
                "change",
            ),
            ("update", "Update the requested NX scope.", ScopeArgs, "update", "change"),
            ("save", "Save a returned part handle.", HandleArgs, "save", "change"),
        ):
            self._register(name, kind, description, args_model, command=command)
        self._register(
            "edit_attribute",
            "change",
            "Edit one attribute on a returned object.",
            AttributeArgs,
            command="edit_attribute",
        )
        self._register(
            "edit_expression",
            "change",
            "Edit one expression on a returned object.",
            ExpressionArgs,
            command="edit_expression",
        )
        for name, description, drawing_args_model, drawing_command in (
            (
                "create_sheet",
                "Create a drawing sheet from a template.",
                CreateSheetArgs,
                "create_sheet",
            ),
            ("add_base_view", "Add a base view to a drawing sheet.", BaseViewArgs, "add_base_view"),
            (
                "add_projected_view",
                "Add a projected drawing view.",
                ProjectedViewArgs,
                "add_projected_view",
            ),
            (
                "add_dimension",
                "Add a dimension between returned entities.",
                DimensionArgs,
                "add_dimension",
            ),
            ("add_note", "Add a note to a returned drawing view.", NoteArgs, "add_note"),
            ("update_views", "Update returned drawing views.", HandleArgs, "update_views"),
            ("export_pdf", "Export a drawing to PDF.", ExportArgs, "export_pdf"),
            ("export_dxf", "Export a drawing to DXF.", ExportArgs, "export_dxf"),
        ):
            self._register(name, "change", description, drawing_args_model, command=drawing_command)

    def kind(self, name: str) -> str | None:
        """The tool's kind (read, session, change), or None when it is not registered."""

        definition = self._tools.get(name)
        return definition.spec.kind if definition is not None else None

    def available(self, name: str) -> bool:
        """Whether the connected bridge can run this tool (C4).

        A tool the bridge does not implement is never offered to the LLM, so
        the model cannot pick an operation that would fail in NX.
        """

        definition = self._tools.get(name)
        if definition is None:
            return False
        if definition.requires is None:
            return True
        if self._capabilities is None:
            self._capabilities = self.backend.capabilities()
        return self._capabilities is None or definition.requires in self._capabilities

    def specs(self) -> list[dict[str, Any]]:
        return [
            tool.spec.model_dump(mode="json")
            for name, tool in self._tools.items()
            if self.available(name)
        ]

    def execute(
        self, name: str, raw_args: dict[str, Any], *, confirmed: bool = False
    ) -> ToolExecution:
        definition = self._tools.get(name)
        if definition is None:
            raise ToolError(f"unknown tool: {name}")
        if not self.available(name):
            raise ToolError(f"the NX bridge in this session does not support {name}")
        try:
            args = definition.args_model.model_validate(raw_args)
        except Exception as exc:
            raise ToolError(f"invalid arguments for {name}: {exc}") from exc
        payload = args.model_dump(mode="json", exclude_none=True)
        if definition.spec.kind == "change" and not confirmed:
            target = payload.get("handle", payload.get("path", "current session"))
            return ToolExecution(
                ok=True,
                needs_confirmation=True,
                preview=(
                    f"Run {name} on {target} with {payload}. One Undo in NX will revert it; "
                    "nothing will be saved."
                ),
            )
        try:
            if definition.handler is not None:
                result = definition.handler(self.backend, args)
            elif definition.command is not None:
                result = self.backend.execute(definition.command, payload).model_dump(mode="json")
            else:
                raise ToolError(f"tool {name} has no implementation")
        except Exception as exc:
            return ToolExecution(ok=False, error=str(exc))
        return ToolExecution(ok=True, result=_model_dump(result))
