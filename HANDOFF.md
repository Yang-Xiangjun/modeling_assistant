# HANDOFF: AI drawing harness (NX-first, PCBA MVP)

This file is the complete brief for implementing the project with Claude Code.
Put it at the repository root. It is self-contained: requirements, architecture,
data contracts, repository layout, and a phased task list with acceptance checks.

**Revision 2026-11-16:** the project owner confirmed assumptions A1 to A8
(section 4.4). Licensing, native NX inputs, three sibling targets, no
Teamcenter, an external LLM for the MVP, and no NX access for Claude Code for
now are settled. Section 16 lists what is still open.

**Suggested first prompt**

> Read HANDOFF.md in full. Create `docs/progress.md` with the task checklist for
> phase P0. List any open question from section 16 that blocks P0. Then do the
> P0 tasks marked `[CC]` in order. Stop when they pass `uv run pytest` and tell
> me exactly what the `[HUMAN]` tasks need from me.

---

## 1. What we are building

A system that generates a 2D engineering drawing for a target 3D model by
learning the conventions of a similar reference model and its existing drawing.

- An **AI harness** plans the drawing (which views, which dimensions, where).
- **Deterministic code** recognises features, measures geometry, lays out the
  sheet and verifies the result.
- **Siemens NX** creates the native, associative drawing through NXOpen journals
  run in batch.

**MVP:** one reference PCBA assembly and its drawing (both native NX part
files), three sibling PCBAs as targets, output as a native NX drawing part plus
PDF and DXF. PCBA is only the first product family. The design must extend to other
automotive actuator parts (housings, gears, shafts, motors, connectors, complete
actuators) by adding product packs, without changing the core.

---

## 2. Rules that override everything

If a task conflicts with one of these, stop and ask.

1. Every measurement comes from the CAD model, never from an LLM or a reference
   drawing.
2. Tolerances, datums and GD&T are never copied from a reference without an
   authoritative source. Without one, they are flagged for human review.
3. The LLM only selects among IDs that deterministic code produced.
4. The harness and services never import a CAD API. Backends run as separate
   processes.
5. A failed check leaves the drawing unreleased and reported, never silently
   saved.
6. Core, harness and worker never name a product type. Product knowledge lives
   in packs.

---

## 3. Your working environment and its limits

The project owner confirmed the points below (status as of 2026-11-16).

- **NX is not installed where you run, for now.** You cannot execute NXOpen
  code. You write the journals; a human runs them on the NX seat and commits
  the output as fixtures. Tasks are tagged:
  - `[CC]` you implement and test it fully.
  - `[HUMAN]` a person must do it on the NX seat. Prepare everything they need
    and stop.
  - `[EXPERT]` a drafting or product expert must decide or review.
- **You may be moved onto the NX machine later.** Check with
  `drawgen ping --backend nx`. If it succeeds, you may run the journals in
  `[HUMAN]` tasks yourself and store their output as fixtures. Recording
  journals in the NX user interface, choosing and exporting real parts, and
  every `[EXPERT]` step stay with people. If it fails, work as described above.
- **Do not invent NXOpen API calls.** Every NXOpen call in `nx_worker/` must be
  either
  1. copied from a journal in `nx_worker/recorded/` (recorded by a human in the
     real NX release), or
  2. listed in section 13 of this file, or
  3. marked with the comment `# UNVERIFIED-NXOPEN` and added to
     `docs/nx_api_assumptions.md` with what needs recording.
  When you need a call that is not available, write the request for a recording
  into `docs/nx_api_assumptions.md` and continue with other work.
- **Do not fabricate real data.** Synthetic fixtures are fine and must carry
  `"synthetic": true`. Never create a file under `fixtures/real/`.
- **Real fixtures may be confidential.** Never paste their content into prompts
  used in tests, logs or documentation.
- **No CAD libraries in this repository** (no pythonOCC, FreeCAD, CadQuery) for
  the MVP. Geometry comes from the worker as JSON.
- Work one phase at a time. At each gate, summarise what passed, what is left
  for people, and wait.
- Keep `docs/progress.md` current. Record every decision this file leaves open
  as a short note in `docs/decisions/NNN-title.md`.

---

## 4. Requirements

### 4.1 Functional (the system shall)

| ID | Requirement | Phase |
|---|---|---|
| FR-01 | Accept a job naming a target model, a reference model and a reference drawing, and record it in a run manifest. | P1 |
| FR-02 | Extract raw geometry and assembly structure from an NX part into JSON without modifying the part. | P1 |
| FR-03 | Extract sheets, views, dimensions, notes, tables and title block from an NX drawing, including the geometry each dimension is attached to. | P1 |
| FR-04 | Build a feature graph with generic features, part class, part frame and geometric fingerprints. | P1 |
| FR-05 | Assign product roles to features through a product pack. The PCBA pack is the first. | P1 |
| FR-06 | Link each reference dimension to features, and list unlinked dimensions with a reason. | P1 |
| FR-07 | Derive a convention profile from the reference: template, views, datum origin, dimension rules per role, notes. | P2 |
| FR-08 | Compile a drawing plan into an execution job and create a native, associative NX drawing in a separate drawing part. | P2 |
| FR-09 | Match target features to reference features, recording method and confidence. | P3 |
| FR-10 | Generate dimension and view candidates by rule, each with an expected value computed from the model. | P3 |
| FR-11 | Produce a drawing plan that selects candidates by ID. Rules decide first; the LLM handles unmatched or ambiguous cases. | P3 rules, P4 LLM |
| FR-12 | Verify every generated drawing against the rule set and emit findings with suggested edits. | P3 |
| FR-13 | Repair by applying edits from a closed set, for at most three rounds, then escalate. | P4 |
| FR-14 | Stop at a review gate with a package: drawing, findings, unresolved items and provenance. | P4 |
| FR-15 | Export native NX, PDF and DXF. | P2 |
| FR-16 | Record a source for every annotation: measured, PMI, requirements document, reference convention or unresolved. | P2 |
| FR-17 | Load product packs through a registry, so a new pack needs no change to core, harness or worker. | P1 interface, P5 proof |
| FR-18 | Run the whole pipeline on recorded fixtures with a mock backend. | P1 |

### 4.2 Quality

| ID | Requirement | Measure |
|---|---|---|
| NFR-01 | Accuracy | A drawing value equals the model measurement within 0.001 mm, or 0.01 degrees for angles. |
| NFR-02 | No model-generated numbers | No dimension value originates from an LLM. The plan schema has no numeric value field, and a test enforces it. |
| NFR-03 | License confinement | Only the NX worker needs a seat. All other tests run in CI without NX. |
| NFR-04 | Reproducibility | The same inputs and plan give the same drawing. Model, prompt and plan version are logged per run. |
| NFR-05 | Extensibility | A second product pack runs end to end with no edits to core, harness or worker. |
| NFR-06 | Backend portability | Harness and services call a backend interface. Contracts carry no NX identifiers except optional hints. |
| NFR-07 | Safety of source data | Source parts are never saved. Output goes to a new drawing part and an output folder. |
| NFR-08 | Data governance | CAD files stay local. Only feature JSON reaches the LLM. A rules-only mode exists, and the provider can be swapped for a locally deployed model by configuration. |
| NFR-09 | Traceability | Every annotation links to a feature, a rule and a run. |
| NFR-10 | Performance (proposed) | One MVP PCBA runs end to end in under 15 minutes on the seat. |

### 4.3 Acceptance criteria

| ID | Criterion | Gate |
|---|---|---|
| AC-1 | At least 90% of reference dimensions are linked to a feature. The rest are listed with reasons. | G1 |
| AC-2 | The reference drawing regenerated from its own extracted plan has the same views and dimension set, with equal values. | G2 |
| AC-3 | For each sibling target, every generated dimension passes the value check and all coverage rules pass. | G3 |
| AC-4 | Every tolerance, datum or note without a source appears in the review package. | G3 |
| AC-5 | An unattended run reaches the review gate on every target in at most three repair rounds. | G4 |
| AC-6 | All service and harness tests pass in CI without NX. | Every gate |
| AC-7 | A second product pack runs end to end with no edits outside its own folder. | G5 |

### 4.4 Confirmed context (project owner, status as of 2026-11-16)

| ID | Confirmed | What it means for you |
|---|---|---|
| A1 | The owner holds NX licenses for all needed functions. | Do not build license checks or fallbacks for missing modules. If a journal fails with a license error, report it from `status.json`; do not work around it. |
| A2 | The same covers authoring Python journals. | Python journals are the worker language. |
| A3 | All 3D models and drawings can be provided as native NX part files. | No PDF, DXF, DWG or STEP parsing in the MVP. Not yet confirmed: whether each drawing is a separate part that references its model. `extract_drawing` must handle both layouts and report `model_part`. |
| A4 | Three sibling PCBAs are available as targets. | The golden set is one reference and three targets. |
| A5 | Teamcenter is not part of the MVP. | Open and save parts by file path. No Teamcenter calls. |
| A6 | Feature JSON may be sent to an external LLM during the MVP. A locally deployed LLM replaces it if that becomes necessary. | The provider must be swappable by configuration (section 12). |
| A7 | Claude Code runs without NX for now and may run on an NX machine later. | See section 3. |
| A8 | The team is 2 to 3 engineers, one with NX drafting experience. | That engineer does the `[HUMAN]` recordings and runs. |

---

## 5. Architecture

Four layers. Dependencies point downward only.

```
AI harness            run state, planner, repair loop, review gate        (P4)
Domain services       generic core + product packs; pure Python; no NX
JSON contracts        versioned schemas; the only thing layers share
CAD backend           CadBackend interface -> MockBackend | NxBackend
                      NxBackend launches nx_worker (NXOpen journals) in batch
```

Import rules (enforced by tests, see P0-T6):

| Package | May import |
|---|---|
| `drawgen_shared` | standard library only |
| `drawgen.contracts` | pydantic, `drawgen_shared` |
| `drawgen.core` | `contracts`, `drawgen_shared` |
| `drawgen.packs.*` | `core`, `contracts`, `drawgen_shared` |
| `drawgen.backends` | `contracts`, `drawgen_shared`, standard library |
| `drawgen.harness` | `core`, `backends`, `contracts`, the pack registry, the LLM client |
| `nx_worker` | standard library, `drawgen_shared`, `NXOpen` |

Nothing under `src/` may import `NXOpen`. Nothing outside `drawgen/packs/` may
contain a pack name such as `pcba`.

### Pipeline

```
 1 read reference model and drawing      backend   -> RawModel, RawDrawing
 2 read target model                     backend   -> RawModel
 3 build feature graphs                  core+pack -> FeatureGraph (x2)
 4 link reference dimensions             core      -> DrawingGraph
 5 build convention profile              core      -> ConventionProfile
 6 match target to reference             core      -> Correspondence
 7 generate candidates                   core+pack -> CandidateSet
 8 plan                                  rules, then LLM for the rest -> DrawingPlan
 9 static check                          core      -> Findings
10 layout and compile                    core      -> ExecutionJob
11 execute                               backend   -> ExecutionReport
12 verify                                core+pack -> Findings
13 repair (max 3 rounds), back to 9      harness
14 review gate, export, package          harness + backend
```

---

## 6. Repository layout

```
HANDOFF.md
README.md
pyproject.toml
docs/
  progress.md               task checklist you keep current
  decisions/                one short note per open decision you settle
  nx_api_assumptions.md     every NXOpen call not yet backed by a recording
schemas/                    JSON Schema exported from the contracts (generated, committed)
shared/drawgen_shared/      stdlib only, Python 3.10 syntax: vectors, fingerprint, matching, json io
src/drawgen/
  contracts/                pydantic models, no logic
  core/
    features/               generic feature recognition on RawModel
    linking.py              RawDrawing attachments -> features -> DrawingGraph
    conventions.py          ConventionProfile builder
    matching.py             target <-> reference Correspondence
    candidates.py           candidates from a drawing graph (P2) and from rules (P3)
    planning.py             rule-based planner, plan validation, edit application
    layout.py               sheet fit, view placement, dimension placement
    compile.py              DrawingPlan + CandidateSet + FeatureGraph -> ExecutionJob
    verify/                 rule engine, static rules, post-execution rules
    packs.py                ProductPack protocol and registry
    manifest.py             RunManifest, artifact store, hashing
  packs/
    pcba/                   first pack (rules, config.yaml, tests data)
  backends/
    base.py                 CadBackend protocol
    mock.py                 replays fixtures, simulates execution, fault injection
    nx.py                   subprocess driver for run_journal
  harness/                  P4: state graph, nodes, llm client, review gate
  cli.py
nx_worker/                  runs inside NX's Python; never imported by src/
  main.py                   reads job.json, dispatches, always writes status.json
  commands/                 ping, extract_model, extract_drawing, execute_plan, measure, export
  nxutil/                   thin NXOpen helpers, each traceable to a recording
  recorded/                 journals recorded by a human in NX (source of truth for API calls)
fixtures/
  synthetic/                generated by tools/make_synthetic.py
  real/                     committed by the human from the NX seat
tools/
  make_synthetic.py
  export_schemas.py
tests/
  unit/  contract/  golden/  arch/
```

---

## 7. Tech stack and conventions

- **Python:** 3.11 or newer for `src/`. `shared/` and `nx_worker/` must run on
  the Python bundled with NX (reported as 3.10 for NX 2406; the human confirms
  the real version in P0-H1). Use 3.10-compatible syntax there and no
  third-party packages.
- **Tooling:** `uv` for environments, `pytest`, `ruff` (lint and format),
  `mypy` in strict mode for `src/` and `shared/`. If the human prefers other
  tools, follow them and note it in `docs/decisions/`.
- **Contracts:** pydantic v2 models. `tools/export_schemas.py` writes JSON
  Schema into `schemas/`. The worker reads and writes plain dicts that conform
  to those schemas.
- **Harness (P4 only):** LangGraph 1.x. Read the documentation of the version
  you install for checkpointers and interrupts; do not rely on memory of the
  API. Pin the version.
- **Units:** millimetres and degrees everywhere. Model coordinates are absolute
  in raw contracts and in the part frame in feature contracts. Sheet
  coordinates are millimetres from the bottom-left corner, y up.
- **Tolerances** live in one config object: linear 0.001 mm, angular 0.01
  degrees, fingerprint matching as in section 8.1.
- **Determinism:** sort every list by a stable key before writing JSON. Hash
  artifacts with sha256 over canonical JSON (sorted keys, no whitespace).
- **Tests:** every public function in `core/` and `shared/` has unit tests.
  Aim for 85% line coverage on `core/` and `shared/`. Golden tests compare
  whole-pipeline outputs on synthetic fixtures against committed expectations.
- **Commits:** small, one task per commit where practical, message prefixed
  with the task ID, for example `P1-T3: generic hole recognition`.
- **CLI:** `drawgen <command>`; every command works against `MockBackend` by
  default and takes `--backend nx` on the seat.

---

## 8. Data contracts (v0)

These are the specification for the pydantic models. You may refine field
names when implementing, but record each change in `docs/decisions/` and keep
rule NFR-02. Every contract has a `schema` string such as `"raw_model/0"`.

### 8.1 Common types

```
Vec3   = [float, float, float]
Pt2    = [float, float]                       # sheet mm, origin bottom-left
BBox3  = [xmin, ymin, zmin, xmax, ymax, zmax]
BBox2  = [x0, y0, x1, y1]
Mat3   = [9 floats, row-major]

Fingerprint
  kind: "face" | "edge"
  geom: "plane" | "cylinder" | "cone" | "sphere" | "torus" | "line" | "circle" | "arc" | "other"
  size: float                 # area for a face, length for an edge
  centroid: Vec3              # model absolute
  direction: Vec3 | null      # plane normal, cylinder or cone axis, line direction, circle normal
  radius: float | null
  bbox: BBox3
  component_path: str | null  # hint only, never required for a match
```

A fingerprint re-finds the same entity in the **same model** across sessions.
It is not used to match target to reference; that is done on features.

Matching (`drawgen_shared.fingerprint.match`):
same `kind` and `geom`; `size` equal within 1e-6 relative or 1e-4 absolute;
`centroid` within 0.001 mm; `direction` parallel within 1e-4 rad, sign ignored;
`radius` within 0.001 mm. Zero matches gives `no_match`, more than one gives
`ambiguous`. Never pick one of several.

### 8.2 Worker output: RawModel

```
RawModel
  schema: "raw_model/0"
  source: {path, units: "mm", nx_version, extracted_at, synthetic: bool, attributes: {str: str}}
  components: [RawComponent]        # flat list, one per occurrence, root included
  bodies: [RawBody]

RawComponent {id, parent_id | null, name, part_name, attributes: {str: str},
              transform: [16 floats, row-major] | null, suppressed: bool}
RawBody      {id, component_id, kind: "solid" | "sheet", bbox: BBox3, volume: float | null,
              faces: [RawFace], edges: [RawEdge]}
RawFace      {id, geom, area, centroid: Vec3, direction: Vec3 | null, axis_point: Vec3 | null,
              radius: float | null, half_angle: float | null, convex: bool | null,
              bbox: BBox3, edge_ids: [str]}
RawEdge      {id, geom, length, start: Vec3 | null, end: Vec3 | null, center: Vec3 | null,
              direction: Vec3 | null, radius: float | null, face_ids: [str]}
```

Entity ids (for example `c3.b0.f17`) are unique within one file and valid only
for that extraction. `convex` tells a boss from a hole; if the worker cannot
determine it, it writes `null` and the core falls back to a heuristic.

### 8.3 Worker output: RawDrawing

```
RawDrawing
  schema: "raw_drawing/0"
  source: {path, nx_version, extracted_at, synthetic: bool, model_part: str | null, attributes: {str: str}}
  sheets: [RawSheet]

RawSheet     {id, name, width, height, scale, projection: "first" | "third" | null, standard: str | null,
              views: [RawView], dimensions: [RawDimension], notes: [RawNote], tables: [RawTable]}
RawView      {id, name, kind: "base" | "projected" | "section" | "detail" | "isometric" | "other",
              parent_id | null, model_view: str | null, rotation: Mat3 | null,   # model -> view
              scale, center: Pt2, bbox: BBox2, representation: str | null, out_of_date: bool | null}
RawDimension {id, view_id | null,
              kind: "linear" | "diameter" | "radius" | "angular" | "ordinate" | "hole_callout" | "chamfer" | "other",
              direction: "horizontal" | "vertical" | "parallel" | "perpendicular" | null,
              value: float | null,            # the measurement as NX reports it
              text: str, text_overridden: bool | null,
              appended_text: {before, after, above, below} | null,
              tolerance: {type: str, upper: float | null, lower: float | null} | null,
              origin: Pt2, bbox: BBox2 | null, retained: bool | null,
              attachments: [RawAttachment]}
RawAttachment {index: int, entity_kind: "face" | "edge" | "point" | "centerline" | "other" | null,
               fingerprint: Fingerprint | null,      # the model entity, when it can be traced
               point: Vec3 | null,
               point_kind: "end" | "mid" | "center" | "tangent" | "intersection" | null,
               view_id | null, trace_note: str | null}   # why tracing failed, if it did
RawNote      {id, text, origin: Pt2, view_id | null, has_leader: bool}
RawTable     {id, kind: "hole_table" | "parts_list" | "tabular_note" | "title_block" | "other",
              origin: Pt2, rows: [[str]]}
```

### 8.4 FeatureGraph

```
FeatureGraph
  schema: "feature_graph/0"
  model_hash: str
  pack: str                       # for example "pcba"
  part_class: str                 # for example "board_assembly", "prismatic", "turned"
  frame: {origin: Vec3, x: Vec3, y: Vec3, z: Vec3, basis: str}
  features: [Feature]
  relations: [Relation]

Feature  {id,
          type: "plane" | "hole" | "hole_pattern" | "boss" | "pocket" | "slot" | "outline"
                | "body" | "component" | "component_group" | "envelope",
          role: str | null,                       # namespaced, for example "pcba.mounting_hole"
          role_source: "rule" | "attribute" | "llm" | "human" | null,
          role_confidence: float | null,
          params: {str: number | str | bool | list},   # in the part frame, for example x, y, diameter, through
          fingerprints: [Fingerprint],
          component_id: str | null, members: [feature id], attributes: {str: str}}
Relation {type: "coaxial" | "coplanar" | "parallel" | "pattern_member" | "mounted_on" | "adjacent",
          a: id, b: id, params: {}}
```

### 8.5 DrawingGraph

```
DrawingGraph
  schema: "drawing_graph/0"
  drawing_hash, model_hash
  sheets: [{id, width, height, scale, projection, standard,
            views: [GView], dimensions: [GDimension], notes: [RawNote], tables: [RawTable]}]
  unlinked: [{dimension_id, reason}]

GView       = RawView + {direction_in_frame: "+X" | "-X" | "+Y" | "-Y" | "+Z" | "-Z" | "iso" | null}
GDimension  {id, raw_id, view_id, kind, direction, value,
             feature_refs: [{feature_id, entity: str}],    # entity: "axis", "face:top", "edge:min_x", ...
             role_signature: str | null,                   # for example "pcba.mounting_hole:position_x"
             tolerance, appended_text, placement: {side, rank}}
```

### 8.6 ConventionProfile

```
ConventionProfile
  schema: "convention_profile/0"
  reference_hash, pack
  template: str | null, sheet: {width, height}, standard, projection
  views: [{key, kind, direction_in_frame, parent_key | null, scale, anchor: Pt2}]   # anchor normalised 0..1
  datum: {x_from: selector, y_from: selector} | null       # for example role + "min_x"
  dimension_rules: [{role_signature, dim_kind,
                     scheme: "ordinate" | "baseline" | "chain" | "single" | "callout" | "table",
                     view_key, placement_side, observed: int, example_raw_ids: [str]}]
  notes: [{text, anchor: Pt2, carry: "flag"}]              # always carried as a review flag
  tolerances_seen: [{role_signature, tolerance}]           # recorded, never applied automatically
  unlinked_count: int
```

### 8.7 Correspondence

```
Correspondence
  schema: "correspondence/0"
  target_hash, reference_hash
  pairs: [{target_id, reference_id, method: "attribute" | "geometry" | "pattern" | "llm" | "human", confidence}]
  target_only: [id], reference_only: [id]
```

### 8.8 CandidateSet

```
CandidateSet
  schema: "candidate_set/0"
  target_hash
  views: [ViewCandidate]
  dimensions: [DimensionCandidate]

ViewCandidate      {id, kind, direction_in_frame, parent_id | null, scale_options: [float], rule_id}
DimensionCandidate {id, role_signature, dim_kind, direction,
                    feature_refs: [{feature_id, entity}],
                    view_ids: [view candidate ids in which it is visible and true length],
                    expected_value: float,        # computed here from the feature graph
                    required: bool, rule_id, source: "measured"}
```

`expected_value` is the only place a dimension value is stored before
execution. It is computed by `core/candidates.py`, never by an LLM.

### 8.9 DrawingPlan and PlanSelection

```
DrawingPlan
  schema: "drawing_plan/0"
  plan_version: int, target_hash, pack
  template, sheet: {width, height}, standard, projection
  views: [{id, candidate_id, scale, center: Pt2}]
  dimensions: [{id, candidate_id, view_id, scheme_group: str | null,
                placement: {side: "above" | "below" | "left" | "right", rank: int}}]
  notes: [{id, text, anchor: Pt2, source: "reference_convention" | "requirement_doc" | "human", flagged: bool}]
  title_block: {str: {value: str, source: str}}
  review_flags: [{id, kind, message, refs: [str]}]
  provenance: {planner: "rules" | "llm" | "human", model: str | null, prompt_hash: str | null}

PlanSelection                       # the only thing an LLM may return for planning
  view_candidate_ids: [str]
  dimension_choices: [{candidate_id, view_candidate_id}]
  role_assignments: [{feature_id, role}]
  review_notes: [str]
```

Neither model has a field for a dimension value (NFR-02). `scale`, `center` and
`rank` are layout numbers set by `core/layout.py`. Every ID in a
`PlanSelection` must exist in the `CandidateSet` or the pack vocabulary;
otherwise reject it, retry at most twice, then fall back to rules-only.

### 8.10 Worker input and output for execution

```
ExecutionJob
  schema: "execution_job/0"
  plan_version, target_part, template, output_drawing
  sheet: {width, height, scale, projection, standard}
  views: [{id, kind, parent_id | null, rotation: Mat3, scale, center: Pt2, representation: "exact"}]
  dimensions: [{id, view_id, dim_kind, direction,
                attachments: [{fingerprint: Fingerprint, point_kind | null}],
                origin: Pt2, scheme_group: str | null}]
  notes: [{id, text, origin: Pt2}]
  title_block: {str: str}
  export: ["pdf", "dxf"]

ExecutionReport
  schema: "execution_report/0"
  plan_version, drawing_part, nx_version, saved: bool
  views: [{id, created: bool, error: str | null, name, bbox: BBox2, scale, out_of_date: bool}]
  dimensions: [{id, created: bool, error: str | null, value: float | null, text,
                associative: bool | null, retained: bool | null, bbox: BBox2 | null}]
  unresolved: [{dimension_id, attachment_index, reason: "no_match" | "ambiguous" | "not_visible_in_view"}]
  exports: [{format, path}]
```

### 8.11 Findings and edits

```
Findings
  schema: "findings/0"
  plan_version
  results: [{rule_id, status: "pass" | "fail" | "warn" | "review", message, refs: [str], edits: [Edit]}]
  summary: {pass, fail, warn, review}

Edit (closed set; the repair loop may use nothing else)
  {op: "move_dimension", id, side, rank}
  {op: "move_view", id, center}
  {op: "set_view_scale", id, scale}
  {op: "set_sheet", width, height}
  {op: "add_dimension", candidate_id, view_id}
  {op: "remove_dimension", id}
  {op: "switch_view", dimension_id, view_id}
  {op: "add_view", candidate_id}
  {op: "flag", message, refs}
```

### 8.12 RunManifest

```
RunManifest
  run_id, created_at
  inputs: {target, reference_model, reference_drawing}
  config: {backend, pack, rules_only: bool, tolerances}
  artifacts: {name: {path, sha256}}
  steps: [{node, started, ended, status}]
  llm_calls: [{node, model, prompt_hash, response_hash}]
```

---

## 9. Worker protocol

The NX backend launches one NX batch process per command:

```
run_journal.exe <repo>\nx_worker\main.py -args <absolute path to job.json>
```

`job.json`:

```json
{
  "protocol": "1",
  "command": "extract_model",
  "inputs": { "part_path": "C:/data/ref_pcba.prt" },
  "output_dir": "C:/runs/2026-11-13_001/extract_model",
  "options": {}
}
```

The worker always writes two files into `output_dir`, even on failure:

- `result.json` the contract payload for the command (absent on failure).
- `status.json` `{ok, command, error: null | {type, message, traceback}, duration_s, nx_version, python_version, log: [str]}`.

| Command | Inputs | Result |
|---|---|---|
| `ping` | none | `{nx_version, python_version}` |
| `extract_model` | `part_path` | RawModel |
| `extract_drawing` | `drawing_part_path` | RawDrawing |
| `execute_plan` | `job_path`, `target_part_path`, `template_path`, `output_drawing_path` | ExecutionReport |
| `measure` | `part_path`, `requests: [{id, kind: "distance" \| "diameter" \| "angle", a: Fingerprint, b: Fingerprint \| null, direction: Vec3 \| null}]` | `{results: [{id, value \| null, error \| null}]}` |
| `export` | `drawing_part_path`, `formats`, `output_dir` | `{exports: [{format, path}]}` |

Worker rules:

- No user-interface calls of any kind; batch mode has no dialogs.
- Native mode only: open and save parts by file path. No Teamcenter calls.
- Open source parts and never save them (NFR-07). Only `execute_plan` saves,
  and only the new drawing part.
- `execute_plan` resolves each fingerprint by reading the loaded model with the
  same code path as `extract_model`, then matching with
  `drawgen_shared.fingerprint.match`. Unresolved entities go into
  `unresolved`; the dimension is skipped, never attached to a guess.
- If any view or required dimension fails, set `saved: false` and do not save
  (rule 5), unless `options.save_on_failure` is true for debugging.
- NXOpen imports stay inside `nx_worker/commands/` and `nx_worker/nxutil/`.
  `main.py` must be runnable in plain Python with `--selftest`, which runs a
  fake command to exercise job parsing and status writing.

`CadBackend` (in `src/drawgen/backends/base.py`) mirrors the commands:

```python
class CadBackend(Protocol):
    def ping(self) -> dict: ...
    def extract_model(self, part_path: Path) -> RawModel: ...
    def extract_drawing(self, drawing_part_path: Path) -> RawDrawing: ...
    def execute_plan(self, job: ExecutionJob) -> ExecutionReport: ...
    def measure(self, part_path: Path, requests: list[MeasureRequest]) -> list[MeasureResult]: ...
    def export(self, drawing_part_path: Path, formats: list[str], output_dir: Path) -> list[ExportedFile]: ...
```

`MockBackend` serves fixtures by path and simulates `execute_plan`: a perfect
executor that returns every `expected_value`, plus switchable faults (wrong
value, missing dimension, overlapping boxes, unresolved entity, stale view) so
the verifier and the repair loop can be tested without NX.

---

## 10. Product packs

```python
class ProductPack(Protocol):
    name: str                                   # "pcba"
    version: str
    def applies_to(self, raw: RawModel) -> float: ...                        # confidence 0..1
    def build_frame(self, raw: RawModel, generic: list[Feature]) -> Frame: ...
    def classify(self, raw: RawModel, generic: list[Feature], frame: Frame) -> list[Feature]: ...
    def dimension_rules(self) -> list[DimensionRule]: ...                     # role -> required dimensions
    def view_rules(self) -> list[ViewRule]: ...                               # default views for this family
    def verification_rules(self) -> list[Rule]: ...
    def vocabulary(self) -> dict[str, str]: ...                               # role -> description, for prompts
```

- Packs register through Python entry points in the group `drawgen.packs`, or
  through an explicit registry call in the pack's `__init__`. The core looks
  packs up by name from config and never imports one directly.
- A pack is mostly data: a `config.yaml` with thresholds and rule tables, plus
  small classifier functions.
- Roles are namespaced strings: `pcba.board`, `housing.bearing_seat`.

### PCBA pack (first pack)

Roles: `pcba.board`, `pcba.board_outline`, `pcba.mounting_hole`,
`pcba.tooling_hole`, `pcba.via`, `pcba.component`, `pcba.connector`,
`pcba.pin`, `pcba.pin_array`, `pcba.envelope_top`, `pcba.envelope_bottom`.

Starting heuristics. These are a first guess, kept in `config.yaml`, and must
be tuned against real fixtures and reviewed by the expert:

- **Board:** the body with the largest pair of parallel planar faces whose
  thickness is under 5% of its shorter in-plane side.
- **Frame:** z is the board normal pointing to the side with more component
  volume; origin and x, y from the outline's bounding rectangle. The
  convention profile may later move the dimensioning datum.
- **Holes:** concave cylindrical faces through the board with axis parallel to
  z. Below `via_max_diameter` (start at 1.0 mm) they are `pcba.via` and are
  ignored for dimensioning. Holes inside a component footprint belong to that
  component. Remaining holes at or above `mounting_min_diameter` (start at
  2.0 mm) are mounting-hole candidates with confidence below 1.
- **Components:** every non-board body or occurrence. Reference designator
  from the occurrence name or attributes with the pattern `^[A-Z]{1,3}\d+`.
  Class from the prefix (`J`, `X`, `P`, `CN` connectors; `U`, `IC` integrated
  circuits; `R`, `C`, `L` passives), configurable.
- **Pin arrays:** four or more identical pins with a regular pitch in one or
  two directions; store rows, columns, pitch and the first and last pin
  positions. Pin 1 cannot be derived from geometry: flag it.
- **Envelope:** maximum height above and below the board faces.

Not derivable from geometry, so always a review flag unless an attribute gives
it: hole plating, pin 1, tolerances, the datum scheme.

Pack verification rules:

| Rule | Check |
|---|---|
| PCBA-01 | Board length, width and thickness are dimensioned. |
| PCBA-02 | Every `pcba.mounting_hole` has x, y and diameter. |
| PCBA-03 | Every `pcba.connector` is located from the datum. |
| PCBA-04 | Every `pcba.pin_array` has pitch and count. |
| PCBA-05 | Maximum height above and below the board is dimensioned. |

---

## 11. Verification rules (generic)

Static rules run on the plan before NX is touched:

| Rule | Check |
|---|---|
| S-01 | Every `candidate_id` and `view_id` resolves. |
| S-02 | Every required candidate is in the plan. |
| S-03 | Each dimension sits in a view listed in its candidate's `view_ids`. |
| S-04 | Predicted view boxes fit inside the sheet margins and do not overlap. |
| S-05 | No duplicate dimension and no closed dimension chain. |
| S-06 | Every note, tolerance and title-block value has a source; items without one have a review flag. |

Post-execution rules run on the `ExecutionReport`:

| Rule | Check |
|---|---|
| V-01 | Each reported value equals the candidate's `expected_value` within tolerance (NFR-01). |
| V-02 | Every planned view and dimension was created. |
| V-03 | Every dimension is associative, not retained, and its text is not overridden. |
| V-04 | The unresolved list is empty. |
| V-05 | Annotation boxes do not overlap each other and stay inside the sheet border. |
| V-06 | Views are up to date and at the planned scale. |
| V-07 | Required title-block attributes are present. |

Each failing result carries suggested edits from the closed set in 8.11 where
one exists. `status: "review"` is for items only a person can judge.

---

## 12. Harness (phase P4)

State graph nodes, in order: `intake`, `read_reference`, `read_target`,
`build_features`, `link_reference`, `build_conventions`, `match`,
`generate_candidates`, `plan_rules`, `plan_llm` (only when unmatched or
ambiguous items remain and `rules_only` is false), `static_check`, `compile`,
`execute`, `verify`, `repair` (loops to `static_check`, at most three rounds),
`review_gate` (interrupt), `export`, `package`.

- State holds artifact references (path and hash), not payloads.
- Checkpoint after every node. A run can resume from any checkpoint.
- LLM access goes through one interface:

  ```python
  class LlmClient(Protocol):
      def select(self, task: str, context: dict, schema: type[BaseModel]) -> BaseModel: ...
  ```

  Provide `FakeLlm` (scripted answers) and a record and replay wrapper for
  tests. An external provider is allowed for the MVP, and a locally deployed
  model may replace it later, so write two thin adapters chosen by config: one
  for the hosted provider the human names (section 16), and one for a
  self-hosted HTTP endpoint whose URL, model name and request format come from
  config. Nothing outside the adapters may depend on a provider feature:
  request JSON, validate it against the pydantic schema, and retry on failure.
  Use the lowest randomness setting the provider offers and log model name,
  prompt hash and response hash.
- The LLM sees only: the candidate list (IDs, role signatures, kinds), the
  unmatched feature list with params, and the pack vocabulary. No file paths,
  no raw geometry dumps.
- `repair` may choose only among edits suggested in `Findings`. If none apply
  or three rounds pass, go to `review_gate` with the open findings.
- `review_gate` writes a review package: drawing and export paths, findings,
  review flags, provenance, and the diff between plan versions. It resumes on a
  human decision: accept, or a list of edits from the closed set.

---

## 13. NXOpen calls seen in published journals

These calls appear in public NXOpen examples. They are a starting point, not a
guarantee for the human's NX release; a recording from the seat always wins.

- Session and parts: `NXOpen.Session.GetSession()`, `session.Parts.Work`,
  `session.Parts.OpenActiveDisplay(path, NXOpen.DisplayPartOption.AllowAdditional)`
  returning `(part, load_status)`, then `load_status.Dispose()`.
- Logging in batch: `session.ListingWindow`, `.Open()`, `.WriteLine(text)`.
- Drawing structure: `part.DrawingSheets` (also `.ToArray()`), `sheet.Name`,
  `sheet.SheetDraftingViews`, `view.Name`, `view.Scale`, `view.IsOutOfDate`,
  `view.Update()`.
- Base view: `part.DraftingViews.CreateBaseViewBuilder(NXOpen.Drawings.BaseView.Null)`,
  `builder.SelectModelView.SelectedView = part.ModelingViews.FindObject("Front")`,
  the `builder.Placement` and `builder.Scale` sub-builders, `builder.Commit()`,
  `builder.Destroy()`.
- Attributes: `obj.GetUserAttributes()` (items have `.Title`),
  `obj.SetUserAttribute(title, -1, value, NXOpen.Update.Option.Now)`.
- Save: `part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)`.
- Dimension attachment: `dimension.NumberOfAssociativities`,
  `dimension.GetAssociativity(i)` (the published loop runs from 1), with
  `.FirstObject` and `.ObjectView` on the result.
- Batch arguments: values after `-args` arrive in `sys.argv[1:]`.

Sources: [NX drawing automation whitepaper](https://inteliscience.net/nx-drawing-automation-whitepaper/),
[NX Journaling: dimension associativity](https://nxjournaling.com/content/auto-balloon),
[Eng-Tips: feature attached to a dimension](https://www.eng-tips.com/threads/nxopen-getting-feature-assoicated-with-dimension.404222/),
[NX Journaling: running a journal in batch](https://nxjournaling.com/content/starting-nx-and-then-running-journal).

Everything else needs a recording, in particular: reading face and edge
geometry, convexity of a cylindrical face, creating a model view with a given
orientation, creating linear, diameter and ordinate dimensions on model edges
in a drafting view, reading a dimension's computed value and retained state,
annotation bounding boxes, title-block fields, and PDF and DXF export.

---

## 14. Phases and tasks

Each phase ends at a gate. Do the `[CC]` tasks, prepare the `[HUMAN]` tasks,
then stop and report.

### P0 Setup (gate G0: a journal runs in batch on the reference files)

- **P0-T1 `[CC]`** Scaffold the repository as in section 6: `pyproject.toml`,
  `uv` environment, `ruff`, `mypy`, `pytest`, a `make check` (or equivalent)
  that runs lint, types and tests, and a CI workflow if the remote supports
  one. *Done when* `make check` passes on a placeholder test. (AC-6)
- **P0-T2 `[CC]`** Implement all contracts from section 8 as pydantic models
  and `tools/export_schemas.py`. Tests: round-trip every model through JSON;
  assert that `DrawingPlan` and `PlanSelection` contain no field that can hold
  a dimension value. (NFR-02, NFR-06)
- **P0-T3 `[CC]`** Implement `drawgen_shared`: vector helpers, frames,
  canonical JSON, hashing, `Fingerprint` computation from a raw face or edge
  dict, and tolerant matching with `no_match` and `ambiguous` outcomes.
  Standard library only, Python 3.10 syntax (set `ruff` target `py310` for
  `shared/` and `nx_worker/`).
- **P0-T4 `[CC]`** `tools/make_synthetic.py`: a parametric PCBA generator that
  writes a valid `RawModel` and a matching reference `RawDrawing`. Parameters:
  board length, width, thickness; mounting holes; vias; box components on both
  sides with reference designators; one or more connectors with a rows by
  columns pin array. The reference drawing has top, bottom and side views,
  outline dimensions, ordinate dimensions for mounting holes from a datum
  hole, connector location, pin pitch, and heights, each with correct
  attachments. Generate one reference and three siblings (one with a different
  board size, one with moved holes, one with an extra connector) under
  `fixtures/synthetic/`, mirroring the real golden set. *Done when* all files
  validate against the schemas.
- **P0-T5 `[CC]`** Worker skeleton and backends: `nx_worker/main.py` with job
  parsing, dispatch, `status.json` on every path and `--selftest`; the `ping`
  command; `CadBackend`, `MockBackend` serving fixtures, and `NxBackend` that
  builds the `run_journal` command line, enforces a timeout, and reads
  `status.json` and `result.json`. Add the CLI command `drawgen ping`.
  Unit-test `NxBackend` with a fake executable. (FR-18, NFR-03)
- **P0-T6 `[CC]`** Architecture tests in `tests/arch/`: no `NXOpen` import
  under `src/` or `shared/`; the import table in section 5 holds; no pack name
  appears outside `src/drawgen/packs/` and its tests; `shared/` and
  `nx_worker/` import no third-party package. (Rules 4 and 6)
- **P0-H1 `[HUMAN]`** Report the NX release and the bundled Python version.
  Say whether each drawing is a separate part that references its model. Put
  the reference PCBA, its drawing and the three sibling PCBAs on the seat as
  native NX part files. Record these journals in NX and commit them under
  `nx_worker/recorded/`: open a part; list sheets and views; read one
  dimension and its attached objects; create a base view and a projected view;
  create one linear dimension between two edges and one diameter dimension on
  a hole; fill a title-block attribute; export a sheet to PDF and to DXF.
- **P0-H2 `[HUMAN]`** Run `ping` through `run_journal` on the seat and commit
  the `status.json`. This is gate G0.

### P1 Read (gate G1: AC-1)

- **P1-T1 `[CC]`** `extract_model` command producing `RawModel`: assembly
  occurrences with names, attributes and transforms; bodies; faces and edges
  with the parameters in 8.2. Use recorded calls; tag the rest. (FR-02)
- **P1-T2 `[CC]`** `extract_drawing` command producing `RawDrawing`, including
  each dimension's attachments traced back to model entities and expressed as
  fingerprints; write `trace_note` when tracing fails. (FR-03)
- **P1-H1 `[HUMAN]`** Run both commands on the reference and the three target
  files.
  Commit the results under `fixtures/real/<name>/`. Send back any
  `status.json` with an error.
- **P1-T3 `[CC]`** Generic feature recognition in `core/features/`: planes,
  holes (coaxial cylinder groups, through or blind, diameter, axis), bosses,
  hole patterns (linear, grid, circular), planar outlines, envelope, and
  components from occurrences. Unit tests on synthetic models. (FR-04)
- **P1-T4 `[CC]`** `ProductPack` protocol, registry, and the PCBA pack from
  section 10 with its `config.yaml`. (FR-05, FR-17)
- **P1-T5 `[CC]`** Linking in `core/linking.py`: match each attachment
  fingerprint to a feature entity, compute `role_signature`, build the
  `DrawingGraph`, and record a reason for every unlinked dimension. (FR-06)
- **P1-T6 `[CC]`** `RunManifest` and artifact store; CLI commands
  `drawgen read` and `drawgen report link-rate`. (FR-01)
- **Gate G1:** on the real reference, link rate is at least 90% and every
  unlinked dimension has a reason. Report the number and the reasons.

### P2 Round-trip (gate G2: AC-2)

- **P2-T1 `[CC]`** `core/conventions.py`: build the `ConventionProfile` from
  the reference `DrawingGraph` and `FeatureGraph`. (FR-07)
- **P2-T2 `[CC]`** `candidates_from_drawing_graph`: turn each linked reference
  dimension into a `DimensionCandidate` on the reference model, with
  `expected_value` recomputed from the feature graph, and each view into a
  `ViewCandidate`. Build the replay `DrawingPlan` from them.
- **P2-T3 `[CC]`** `core/layout.py` and `core/compile.py`: view placement from
  the profile anchors, dimension origins from placement side and rank, view
  rotation from frame and direction, and the `ExecutionJob`. (FR-08)
- **P2-T4 `[CC]`** Worker commands `execute_plan`, `measure` and `export`,
  written from the recordings. Create the drawing as a separate part that
  references the model. (FR-08, FR-15, NFR-07)
- **P2-T5 `[CC]`** Verification engine with rules S-01 to S-06 and V-01 to
  V-07, and `MockBackend` execution with fault injection. (FR-12, NFR-01)
- **P2-T6 `[CC]`** Provenance on every plan item and a review-package
  skeleton. `drawgen compare` diffs two `DrawingGraph`s: view set, dimension
  set by role signature and feature, and values. (FR-16, NFR-09)
- **P2-H1 `[HUMAN]`** Run the round-trip on the seat, then run
  `extract_drawing` on the generated drawing and commit both the
  `ExecutionReport` and the new `RawDrawing`.
- **Gate G2:** `drawgen compare` between the original and the regenerated
  reference shows the same views and the same linked dimensions with equal
  values. On failure, change the plan schema rather than adding executor
  workarounds.

### P3 Transfer (gate G3: AC-3, AC-4)

- **P3-T1 `[CC]`** `core/matching.py`: target to reference `Correspondence`
  by attribute (reference designator, part number), then role and normalised
  position in the frame, then patterns. Record method and confidence. (FR-09)
- **P3-T2 `[CC]`** `candidates_from_rules`: apply the profile's
  `dimension_rules` and the pack's `dimension_rules` to the target's features
  to produce a `CandidateSet` with expected values. (FR-10)
- **P3-T3 `[CC]`** Rule planner in `core/planning.py`: select required
  candidates, follow the profile's views and schemes, choose sheet scale by
  fit, and raise a review flag for every unmatched or ambiguous feature. No
  LLM yet. (FR-11)
- **P3-T4 `[CC]`** PCBA rules PCBA-01 to PCBA-05 and a metrics report per
  target: dimensions planned, created, verified, unresolved, flags, run time
  per step, and a `human_edits` field for the reviewer. (FR-12, NFR-10)
- **P3-H1 `[HUMAN]` `[EXPERT]`** Run on the three sibling targets. The expert reviews
  each drawing in NX and records the number of edits needed.
- **Gate G3:** every generated dimension passes V-01, all coverage rules
  pass, and every unsourced tolerance, datum or note is in the review
  package. The share of unmatched features decides how much LLM planning P4
  needs.

### P4 Harness (gate G4: AC-5)

- **P4-T1 `[CC]`** State graph from section 12 in rules-only mode, with
  checkpoints and the `RunManifest`. It must reproduce the P3 pipeline
  exactly. (NFR-04)
- **P4-T2 `[CC]`** `LlmClient`, `FakeLlm`, record and replay, and the two
  provider adapters from section 12, selected by config. (NFR-08)
- **P4-T3 `[CC]`** `plan_llm` node: prompt from candidates, unmatched features
  and vocabulary; `PlanSelection` output; validation, two retries, fallback to
  rules. (FR-11, NFR-02)
- **P4-T4 `[CC]`** `repair` node and edit application, at most three rounds.
  (FR-13)
- **P4-T5 `[CC]`** `review_gate` with interrupt and resume, and the full
  review package. (FR-14)
- **P4-T6 `[CC]`** End-to-end tests on synthetic fixtures with `MockBackend`
  and `FakeLlm`, including each injected fault, proving the loop terminates
  and the gate is reached.
- **P4-H1 `[HUMAN]`** Unattended runs on the seat for every target.
- **Gate G4:** every target reaches the review gate in at most three repair
  rounds with a complete run log. The MVP is done.

### P5 Generalise (gate G5: AC-7)

- **P5-T1 `[CC]`** A synthetic housing generator (a prismatic body with two
  bearing bores, mounting lugs with holes, and a sealing face) and its
  reference drawing, under `fixtures/synthetic/`.
- **P5-T2 `[CC]`** A `housing` pack: roles such as `housing.bearing_seat`,
  `housing.mounting_hole`, `housing.sealing_face`, `housing.datum_face`;
  dimension rules for bore diameters, centre distance, hole positions and
  overall size; its verification rules. The expert supplies or corrects the
  rules.
- **P5-T3 `[CC]`** Run the housing through the whole pipeline. *Done when* the
  change set touches only `src/drawgen/packs/housing/`, fixtures and tests.
  Any change needed elsewhere is a defect in the interface: fix it
  generically, list it in `docs/decisions/`, and re-run the PCBA golden tests.
  (NFR-05)
- **P5-T4 `[CC]`** Freeze the contracts as v1: bump the `schema` strings,
  regenerate `schemas/`, and write migration notes.
- **P5-H1 `[HUMAN]` `[EXPERT]`** Provide a real housing and its drawing and
  review the result.

### Later, out of scope for this handoff

STEP and IDX targets, references that exist only as PDF or DXF, section and
detail views, parts lists and balloons, GD&T, an independent OCCT cross-check,
a second CAD backend, Teamcenter-managed mode.

---

## 15. Definition of done for any task

- Code is typed, formatted, and passes `make check`.
- New behaviour has unit tests; pipeline changes update golden expectations
  with a reason in the commit message.
- No rule in section 2 is broken; the architecture tests pass.
- `docs/progress.md` is updated, and any new unverified NXOpen call is listed
  in `docs/nx_api_assumptions.md`.
- For worker code: the journal is runnable by the human with one documented
  command, and its failure modes write a useful `status.json`.

---

## 16. Open questions: ask, do not assume

Answered on 2026-11-16 and removed from this list: licensing, native NX inputs,
the number of targets, Teamcenter, and whether feature JSON may leave the
network (section 4.4).

1. Which NX release and bundled Python version is on the seat?
2. Is each drawing a separate part that references its model, or do the sheets
   live in the model part?
3. Which drafting standard and template does the reference use, and where is
   the template file?
4. Which hosted LLM provider and model should P4 use?
5. May real fixtures be committed to this repository, or must they stay in a
   local folder that is ignored by version control?
6. Which reference-designator and attribute conventions do the PCBA
   assemblies follow?
7. Where does the repository live, and which CI system should the workflow
   target?
