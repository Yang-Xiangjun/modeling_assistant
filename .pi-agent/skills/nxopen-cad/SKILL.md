---
name: nxopen-cad
description: Use the Branch C NXOpen bridge for typed CAD inspection and operations.
---

# Branch C NXOpen CAD skill

Use the supplied Branch C tools to operate on the live interactive NX session.
The tools call a C# NXOpen bridge inside NX. Do not write or execute ad hoc
NXOpen, shell, or journal code in a response.

## Plan-first request handling

Classify every request as simple, complex, or ambiguous. For a complex or
ambiguous request, ask concise clarification questions before executing NX.
Build an operation plan with the goal, selected entities, preconditions, ordered
steps, expected outputs, units, and fallback paths.

For each planned step, expand user wording into NX terminology and search the
read-only NXOpen API catalog, verified journals, and project API notes. Confirm
the candidate signature and object compatibility before selecting a typed tool.
If a candidate fails, record the error, update the plan, search the next synonym
or related API, and retry. Runtime execution uses validated Branch C adapters.

## Selection and measurements

For a request about the selected object, call `get_selection` first and use the
returned `handle`.

Use the `measure` tool with a request shaped like this:

```json
{
  "requests": [
    {"id": "m0", "kind": "area", "a": "tag:12345"}
  ]
}
```

The measurement is typed by the selected NX object.

- A `Face` returns that face area.
- A `Body` returns the sum of all `Body.GetFaces()` areas.
- A body feature such as `Block` returns the sum of the faces of each body from
  `BodyFeature.GetBodies()`.
- A solid `Body` or body feature can return volume through mass properties.

When the user asks for the surface or total surface area of a selected block,
body, or solid, read the selection and measure `area` on its handle. Report the
value and `mm2` only after the tool returns it. Never calculate a value from
the nominal block dimensions when NX can return the live result.

When the user asks for volume, read the selection and use the typed volume
measurement on a solid body or body-feature handle. Search terms include
`volume`, `solid volume`, `mass properties`, `body volume`, and `centroid`.
Use `MeasureManager.NewMassProperties` with `MeasureBodies.Volume` when that
adapter is available. Report the returned value and unit from NX.

The C# implementation uses these NXOpen APIs:

- `NXOpen.Features.BodyFeature.GetBodies()`
- `NXOpen.Body.GetFaces()`
- `NXOpen.MeasureManager.NewFaceProperties(Unit, Unit, double, IParameterizedSurface[])`
- `NXOpen.MeasureManager.NewMassProperties(...)`
- `NXOpen.MeasureBodies.Volume`

If no object is selected, ask the user to select the target in NX. If the
selected object is incompatible with the requested operation, explain the
required entity type and ask for a new selection. If NX returns an error, report
that error, update the plan, and do not invent a measurement.

## Box and through-hole creation

Use `create_box_with_hole` for a requested box and through-hole. Dimensions are
in millimetres. If the user specifies the hole-center distance from the left or
bottom boundary, pass those values as `hole_center_left` and
`hole_center_bottom`. Omit either field when the user did not specify it. The
bridge uses the box center for omitted offsets and rejects a center that would
place any part of the hole outside the box.

## Operation discipline

Return one valid `AssistantStep` JSON object. Emit a listed tool call for an
operation and answer concisely after a successful result. Do not repeat a
successful tool call. Use `ask_user` for clarification, missing selection, or
an operation that requires a different entity type. There is no numeric
operation step limit. Stop when the pipeline succeeds, candidate APIs are
exhausted, the request needs clarification, or NX reports an unrecoverable
failure.
