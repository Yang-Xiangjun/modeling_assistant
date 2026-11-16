# 009 Contract refinements against HANDOFF.md section 8

Status: decided 2026-11-16 (P0-T2). NFR-02 is kept and tested.

- **`schema` field.** pydantic reserves the attribute name, so the Python field is
  `schema_` with the alias `schema`. JSON always says `schema`.
- **Strict models.** Every model rejects unknown fields, NaN and infinity.
- **Geometry enums.** `RawFace.geom` and `RawEdge.geom` use the face and edge
  subsets of the fingerprint `geom` list. Anything else is `other`.
- **Timestamps** (`extracted_at`, `created_at`, step times) are ISO 8601 strings,
  not datetimes, so re-serialising never changes an artifact hash.
- **Transforms** are 16 floats, row-major (`Mat4`).
- **`PlanSelection` and `RunManifest`** get schema strings `plan_selection/0` and
  `run_manifest/0`; section 8 gives them none.
- **Worker protocol messages** (`job.json`, `status.json`, ping, measure and
  export results) are models in `contracts/worker.py`. They carry no schema
  string; the `protocol` field of `job.json` versions them.
- **`ConventionProfile.datum` selectors** are `{role, entity}`.
- **`GDimension.placement`** is `{side | null, rank}` or null, because a side may
  not be derivable from a reference. `DrawingPlan` placements are always complete.
- **`ExecutionReport`** view and dimension detail fields are nullable, since an
  item that was not created has no name, box or value.
- **`Findings.summary.pass`** is `pass_` in Python (keyword), `pass` in JSON.
- **`Tolerances`** is the one tolerance object, with the defaults of sections 7
  and 8.1. It sits in `RunManifest.config`.
- **NFR-02 test.** It walks the JSON Schemas of `DrawingPlan` and `PlanSelection`
  and requires the set of numeric or untyped locations to equal an allow-list:
  plan version, sheet width and height, view scale and centre, placement rank,
  note anchor. `PlanSelection` must have none.
