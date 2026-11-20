# Branch C implementation plan: NX chat assistant

Status: planning document for the open-ended Branch C MVP  
Scope: C0 Bridge spike through C3 Connect  
Goal: accept chat input beside NX, clarify complex requests, plan operation steps, discover and validate NXOpen APIs, compose typed pipelines, and execute them through the live bridge.

This plan follows `HANDOFF.md` sections 5, 6, 14, and 17. The drawing track remains separate; the assistant starts it only in C3.

## Scope and constraints

At completion, a separate chat window can query the interactive NX session, answer inspection questions, plan open-ended requests, discover related NXOpen APIs, validate candidate pipelines, preview and execute supported adapters, and start the drawing harness. The LLM can return only an answer, clarification, or typed tool calls.

Keep these rules enforced:

- only `nx_bridge/` imports NXOpen;
- bridge handles are session-local and invalidated after context/part changes;
- the bridge listens on `127.0.0.1` with a per-session token;
- listener threads queue work to NX's main thread and never call NXOpen directly;
- timeouts are returned as errors and never replayed;
- changing tools require explicit panel confirmation, set one undo mark, and never save implicitly;
- no tool accepts free-form code, journals, shell commands, or executable paths;
- numeric answer values must come from the user or same-turn tool results;
- complex requests require clarification before execution;
- API discovery is read-only and never executes model-generated NXOpen code;
- changing operations use compiled, versioned, typed bridge adapters;
- geometry editing, Teamcenter, remote/multi-user use, and an embedded NX panel remain out of scope.

## MVP priorities

The MVP prioritizes the planning and discovery loop over a large hard-coded operation list.

1. Accept the user's wording and classify the request as simple, complex, or ambiguous.
2. Ask concise clarification questions for complex or ambiguous requests before building an execution plan.
3. Build an `OperationPlan` with confirmed goal, entities, preconditions, ordered steps, outputs, units, and fallback strategies.
4. Search API synonyms and verified project evidence for each planned step.
5. Validate candidate APIs against NX2506 and compose a typed pipeline from validated adapters.
6. Replan after a failed candidate until a candidate succeeds, candidates are exhausted, clarification is required, or NX reports an unrecoverable failure.
7. Keep the existing area and box capabilities working while adding volume as the first new vertical slice.

There is no numeric operation step limit. Replanning ends through candidate exhaustion, repeated-candidate detection, clarification, or a real NX failure.

RSI receives lower priority in the MVP. The MVP records plans, API candidates, results, and failures for later analysis. Adaptive API ranking, high-frequency API promotion, and automatic failure summarization are post-MVP work.

## Entry decisions before bridge code

Record A9–A13 and bridge choices in `docs/decisions/`:

| Decision | Working default | Evidence |
|---|---|---|
| A9 | Separate Tkinter window beside NX | 1920x1080 co-visibility check |
| A10 | Planning-driven typed capabilities, starting with inspection, area/volume measurement, and the existing box operation | Owner confirmation |
| A11 | **Confirmed direction:** compiled C# NXOpen add-in | Exact NX/.NET/build/load details and recordings |
| A12 | Pi as the default MVP harness, with Codex and FakeHarness adapters retained | Owner-selected harness direction |
| A13 | One client, one NX session, same Windows machine | Token/port single-client test |
| Transport | Newline-delimited JSON over loopback TCP | Fake-bridge and seat smoke tests |
| Dispatch | Listener queues to NX UI/main-thread callback | Recorded journal |

If the selected bridge cannot keep NX responsive, stop at GC0 and change the approach before C1.

## Harness portability requirement

The assistant and drawing harness must depend on a provider-neutral `HarnessAdapter`/`LlmClient` port. Codex CLI, Claude Code, Pi, and future harnesses are adapters behind that port; no concrete CLI may be imported by `assistant/`, `tools/`, or the bridge.

Before C1-T4, confirm the first supported CLI, its version and command line, structured JSON request/response format, tool-call support, streaming/cancellation behavior, timeout and exit-code semantics, authentication, session/context handoff, and whether tool results may leave the machine. `FakeHarness` plus record/replay traces are the CI contract, so adding another CLI must not change assistant or bridge code.

## Files and contracts

Add:

```
src/drawgen/contracts/live.py
src/drawgen/contracts/operation_plan.py
src/drawgen/backends/{live,live_mock,bridge}.py
src/drawgen/assistant/{agent,checker,log,planning,api_search}.py
src/drawgen/assistant/tools/{__init__,common,inspect,model,drawing,pipeline}.py
src/drawgen/assistant/panel/{app,controller}.py
nx_bridge/{README.md,src/,recorded/}
fixtures/synthetic/live/
tests/assistant/ tests/integration/assistant/
```

Register live schemas and regenerate `schemas/`. Define strict models for:

- `BridgeRequest`/`BridgeResponse`;
- `PartRef`, `SessionContext`;
- `Selection`/`SelectedObject` with handle, entity kind, component path, fingerprint, and measured properties;
- handle-based live measurements for area, volume, mass, centroid, bounding box, length, radius, diameter, distance, and angle;
- `ListRequest` and `OperationResult` with undo mark and saved/changed flags.
- `OperationPlan`, `PlanStep`, `ApiCandidate`, `PipelineStep`, and `PipelineResult`;
- API evidence with source path, signature, assembly, NX version, validation status, and failure reason.

Keep live measurement models separate from batch fingerprint-based `MeasureRequest`. If the bridge is C#, return normalized geometry facts and compute canonical fingerprints in Python with `drawgen_shared`.

## C0 Bridge spike (GC0)

1. Implement `LiveBackend` and `MockLiveBackend` with scripted context/selections and faults for timeout, bad token, empty/ambiguous selection, dialog stall, and failed change.
2. Add synthetic live fixtures and `drawgen live ping` / `drawgen live selection`.
3. Implement the minimum bridge: `ping`, `get_selection`, selected-face area, token validation, request-ID echo, main-thread dispatch, short slices, and session-local handles.
4. Implement `BridgeBackend` with endpoint discovery, bounded timeout, malformed-response handling, ID checking, and no replay.
5. Add a logic-free panel that only renders selection results.
6. Put every unrecorded NXOpen call in `docs/nx_api_assumptions.md` with `# UNVERIFIED-NXOPEN`.

Human gate: build/load the bridge, compare outside-process face area with NX's measure command, repeat after rotation and with an NX dialog open, and record latency and NX usability. GC0 passes only when the value meets NFR-01 and NX remains usable.

## C1 Inspect (GC1)

Add bridge commands `get_context`, expanded `get_selection`, `measure`, and `list`. Read all values from live NX objects; never resolve targets from descriptions.

Add a read-only `search_nx_api` path backed by the local NXOpen API index, HTML reference pages, verified journals, and `docs/nx_api_assumptions.md`. It returns candidate methods and properties with exact signatures and source evidence. Synonym expansion searches user terminology and NX naming variants such as `volume`, `mass properties`, `solid volume`, and `centroid`.

Register typed tools for context, selection, measurements, API search, lists of attributes/expressions/features/components/sheets/views/dimensions, and selected feature/role lookup. The role tool remains unavailable until P1's `FeatureGraph` exists.

Implement:

- deterministic `ToolSpec` registry and argument/result validation;
- `assistant/agent.py` using `LlmClient`/`FakeLlm`, clarification for complex or ambiguous requests, progress-driven replanning, and no numeric tool-round cap;
- `assistant/planning.py` for request classification and `OperationPlan` creation;
- `assistant/api_search.py` for synonym expansion, local API search, candidate scoring, and NX2506 validation;
- `assistant/pipeline.py` for typed pipeline composition and candidate fallback handling;
- number checker that rejects unsupported numbers, allows displayed-precision rounding, retries once, then falls back to raw tool results;
- JSONL session log under `runs/assistant/<session_id>/` with message, model/prompt hashes, calls, results, confirmations, checker verdicts, and answers;
- thin panel with off-loop agent execution;
- `drawgen assistant eval` reporting accuracy and wrong-answer causes.

Human gate: expert provides the 20-face set and inspection questions; the NX owner records journals, runs the set, and checks AC-11. GC1 passes AC-8, AC-9, and AC-11.

## C2 Operate (GC2)

Implement the shared change controller before operations:

1. validate typed args and handles;
2. build and render a preview with target and old/new values;
3. highlight the target;
4. wait for an explicit panel confirmation;
5. set one undo mark and execute once;
6. return the result and “one Undo in NX reverts this”;
7. never save implicitly.

Session tools with no confirmation: `open_part`, `switch_part`, `orient_view`, `fit_view`, `highlight_entity`.

Changing model tools with confirmation + undo: `show_entity`, `hide_entity`, `isolate_entity`, `edit_attribute`, `edit_expression`, `update`, `save`. Expression values must come from the user or tool results.

Changing drawing tools: `create_sheet`, `add_base_view`, `add_projected_view`, `add_dimension`, `add_note`, `update_views`, `export_pdf`, `export_dxf`. Reuse common operation payloads with the worker where possible; otherwise implement bridge commands from C2 recordings.

Add the first plan-driven measurement adapter for selected body volume. Validate the candidate `MeasureManager.NewMassProperties` and return `MeasureBodies.Volume` with the NX unit. Preserve area measurement and add fallback validation through the available NXOpen mass-property APIs when the primary candidate fails.

Operation eval cases must assert preview, confirmation, post-state, one-Undo state, and save behavior. Mock tests must prove no confirmation means no change, one change means one undo mark, save is never implicit, timeouts are not replayed, and stale/ambiguous handles are rejected.

Human gate: record one journal per operation, rebuild, run the operation set from chat, and verify one Undo per operation. GC2 passes AC-10.

## C3 Connect (GC3)

Add `generate_drawing_for_work_part`:

- read context and refuse a missing work part;
- report unsaved changes and ask the user to save explicitly;
- start the existing harness and stream progress;
- render native drawing/PDF/DXF paths, findings, review flags, unresolved items, provenance, and run ID.

Only this tool may import `drawgen.harness`. Test with `MockLiveBackend`, `MockBackend`, and `FakeLlm`. Human validation runs “Generate the drawing for this part” on real targets. GC3 passes AC-13.

## Validation and commit order

Run `make check` after every slice:

1. C0 contracts, schemas, mock backend, and fixtures.
2. C0 backend client, CLI, fake bridge tests, and bare panel.
3. C0 recorded bridge and README; then close GC0.
4. C1 bridge commands, API search, planning contracts, registry, agent, checker, log, panel, and eval; then close GC1.
5. C2 typed pipeline composer, volume adapter, change controller, model/drawing tools, recordings, and Undo eval; then close GC2.
6. C3 pipeline tool, progress/review rendering, and end-to-end mock test; then close GC3.
7. Post-MVP RSI analysis for high-frequency APIs, synonym promotion, and failure summaries.

MVP completion also requires complex-request clarification, API evidence for every plan step, candidate replanning after failures, and a validated NX2506 volume vertical slice.

Branch C is done when GC0–GC3 and AC-8–AC-13 have evidence, CI passes without NX, every live tool has typed MockLiveBackend tests, every change tool has a no-confirmation test, every bridge NXOpen call has a recording/assumption entry, `nx_bridge/README.md` is usable by the NX-seat engineer, and `docs/progress.md` records the gate evidence.

