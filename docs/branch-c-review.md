# Branch C review and flexibility plan

Status: review of commit `d3923a8` (Branch C MVP), 2026-11-20. Basic review and
plan only; nothing here is implemented yet. Target runtime: Windows, NX 2506
(.NET 8 host), Python 3.12 via `uv`, the `pi` CLI as harness, a C# bridge
loaded into the interactive NX session.

Method: three independent Codex reviewers (blind first pass), then consensus
with every blocking finding re-checked against the code. Raw reports and the
vote table are in `_code_reviews_ai/run_20261120_053039/cycles/cycle_01/`.

Owner goal ("flexibility"): the assistant supports many kinds of NX operation,
not a fixed handful. For each request, pi plans the operation, looks up the
NXOpen API, and forms an NXOpen C# pipeline that does what the user asked.

## Status update (Python-side fixes)

These commits on top of the review fix the Python side. The C# bridge is
unchanged: it cannot be built or run on the review machine, and CLAUDE.md
forbids inventing NXOpen calls.

| Commit | Fixes | What changed |
|---|---|---|
| C-R0-1 | C1, C8 (browser), S8 (browser), S11 | The UI server runs in-process sessions, one agent per tab. A change pauses on the exact call it previewed until the page sends that turn's confirmation ID. There is no auto-confirm. A per-launch token and JSON-only POSTs are required. |
| C-R0-2 | C6 | Numeric arguments of session and change tools must come from the user or a tool result. The checker matches at the precision shown, counts list lengths, and ignores digits inside identifiers. One retry, then raw results. |
| C-R0-3 | S12, C8 (agent) | Clear requests and non-English text are no longer blocked. A clarification answer completes the original request. |
| C-R0-4 | C7 | A timed-out session or change command raises `LiveOutcomeUnknown` and is never resent. Changes get their own 60 s deadline. |
| C-R1-1 | C4 (Python side) | The registry offers only tools that the connected bridge runs. `capabilities()` falls back to the 11 commands both C# dispatchers implement. |

Still open, all needing C# or an NX seat: C2 (real undo marks), C3 (add-in
main-thread queue), C5 (handle table), S3, S5, S6, S7, S10, and the C# side of
C4 (answering `capabilities` from the manifest).

## 1. Summary

- The Python side is a sound base. It has typed contracts, a provider-neutral
  harness port with fake, OpenAI Responses and pi adapters, a closed tool
  registry, a confirmation callback, a number checker and a JSONL log. The
  smoke runtime that the journal loads dispatches NXOpen calls on NX's UI
  thread through a timer queue.
- The flexibility goal is not reached. API lookup only adds text to the prompt.
  `PipelineStep` and `PipelineResult` exist as contracts but nothing builds or
  runs them. The bridge implements 11 hard-coded commands, while the LLM is
  offered about 30 tools.
- The live change path is unsafe today. The browser UI confirms every change
  automatically, most changes report an undo mark that was never set, and
  handles are raw NX tags that never expire.
- The goal as stated conflicts with CLAUDE.md rule 7 ("never runs NXOpen code
  written by a model"). Section 4 gives a design that meets the goal without
  breaking the rule, and the decision the owner must make if runtime-generated
  C# is still wanted.

## 2. Plan vs what is built

| Plan item | Status | Evidence |
|---|---|---|
| Live contracts (HANDOFF 17.3) | Done, partly filled | `contracts/live.py`. The bridge always returns `fingerprint` and `component_path` as null and `modified` as false. |
| `MockLiveBackend` with faults | Partial | Scripted data only. No timeout, bad-token, ambiguous-selection, dialog-stall or failed-change faults. |
| `BridgeBackend` | Mostly | Checks the endpoint and the echoed ID, never replays. No "outcome unknown" after a timeout. |
| Bridge on NX's main thread | Split | Smoke runtime: timer queue, correct. Add-in `NxBridgeEntry`: calls NXOpen from the listener task. |
| `get_context`, `get_selection`, `measure` | Partial | Only area and volume are measured. The contract also lists length, radius, diameter, distance and angle. |
| `list`, open/switch part, orient view | Missing in the bridge | Registered in Python, absent from both C# dispatchers. |
| Attribute, expression, drawing and export tools | Missing in the bridge | Same as above. |
| `search_nx_api` and planning | Partial | Keyword classifier and TSV search. Evidence is not used to choose or run anything. |
| Pipeline composer and replanning | Missing | No `assistant/pipeline.py`. A failed tool ends the turn. |
| Number checker | Partial | Exact match. No rounding, counts, retry or tool-argument check. |
| Change path (HANDOFF 17.6) | Unsafe | Preview string only. No highlight, no old/new values. Undo marks are fake. The browser confirms automatically. |
| Session log | Partial | No confirmation, model or prompt-hash records. The browser writes one log per message. |
| Panel | Two exist | Tk window and browser page. A9 is not decided. |
| Volume slice | Works offline | Calls `NewMassProperties` through reflection. Not listed in `docs/nx_api_assumptions.md`. |
| `create_box_with_hole` | Works offline | Geometry creation, which A10 puts outside the MVP. The scope change is not recorded. |
| C3, drawing generation from chat | Not started | Expected: the drawing pipeline (P1 to P4) does not exist yet. |
| Gates GC0 to GC3, decisions C0-T4 | Open | `docs/progress.md` still says no C0 work is done. |

## 3. Review results

Each item has a fix direction. IDs match `consensus.md`. All file references
are to `d3923a8`.

### 3.1 Must fix before using the bridge on a real part

| ID | Defect | Where | Fix direction |
|---|---|---|---|
| C1 | The browser UI confirms every change automatically | `tools/branch_c_ui_server.py:67,98-99`, `tools/start_branch_c_ui.ps1:19` | Remove `--yes` and the auto-confirm flag. The browser shows the preview and sends an explicit confirm or cancel (section 5.2). |
| C2 | Undo marks are fake (`"branch_c_display"`, `"branch_c"`) or null; only `update` sets one | `BranchCSmokeRuntime.cs:280,623-647`; `NxBridgeEntry.cs:322-344,352-440` | One C# wrapper calls `SetUndoMark` before every change handler and returns the real mark ID. The Python side rejects `changed: true` with a null mark. |
| C3 | The add-in runs NXOpen on the listener thread | `BridgeServer.cs:51-72`, `NxBridgeEntry.cs:49-74` | Use the smoke runtime's main-thread queue in the add-in, then merge the two dispatchers (S7). |
| C4 | The LLM is offered tools the bridge cannot run | `tools/__init__.py:262-349` | Bridge `capabilities` command; the registry keeps only what the loaded bridge supports (section 4.3). |
| C5 | Handles are raw tags with no lifetime; `save` ignores its handle | `NxBridgeEntry.cs:443-470`, `BranchCSmokeRuntime.cs:650-669` | A handle table in the bridge keyed by session and part generation. Reject stale handles. `save` saves the part named by the handle. |
| C6 | Numbers in tool arguments are never checked; the answer checker rejects rounded values and counts | `agent.py:51-78`, `checker.py:30-38` | Each numeric argument must appear in a user message or a tool result. Match answers at the displayed precision, and take counts from list lengths. |
| C7 | A timed-out change is reported as a generic failure | `bridge.py:48-61`, `BridgeServer.cs:63-72` | Return a distinct `outcome_unknown` state. The agent tells the user to check NX and never retries the change. |
| C8 | Clarification and conversation state is lost | `branch_c_ui_server.py:72-117`, `agent.py:41-50` | A long-running assistant service keeps one agent, its pending plan and its pending confirmation per session (section 5.2). |

### 3.2 Important

| ID | Finding | Fix direction |
|---|---|---|
| S1 | Plan, API lookup and pipeline are not connected to execution | Section 4. This is the main flexibility gap. |
| S2 | The preview has no target name, no old/new values and no highlight; the browser shows no tool calls | Typed preview built by the bridge; the panel renders each step, its result and its undo mark. |
| S3 | Context and selection fields are hard-coded or null; only area and volume are measured | Fill `modified`, `component_path` and geometry facts. Compute fingerprints in Python with `drawgen_shared`. |
| S4 | Windows portability (section 6) | Pass the repository root and paths through configuration, not literals. |
| S5 | Endpoint file has no user-only ACL; the client trusts `host`; the two load paths provision the token differently; several clients are accepted | Write the file with a user-only ACL, accept only `127.0.0.1`, provision the token one way, allow one client. |
| S6 | The smoke runtime parses JSON with regexes (`measure` depends on field order) and drains the whole queue in one UI tick | Use `System.Text.Json` and a per-tick time budget. |
| S7 | Two diverging dispatchers; one new operation means about 7 edits | One bridge assembly with one handler per command (section 4.3). |
| S8 | The log lacks tool-call, confirmation, model and prompt-hash events | Add those events and keep one log per conversation. |
| S9 | Tests cover only the mock, which invents undo marks | Fault-injecting mock, protocol fixtures shared with C#, no-confirmation-no-change tests per change tool. |
| S10 | The default launch creates and saves a fixture part before any confirmation | Make the fixture opt-in, saved to a scratch folder, never touching the user's part. |
| S11 | The UI server accepts cross-origin `POST /api/chat` with any content type. With C1, a web page open in the same browser could send commands to NX | Require `application/json` and check `Origin`, plus a per-launch token in the page. |
| S12 | The planner marks clear requests as ambiguous ("hide this body", "save the part", any non-English text) | Build clarification from what the chosen operation still needs, not from English verb lists (section 4.2). |

### 3.3 Needs a decision or an NX seat

| ID | Item |
|---|---|
| N1 | Round cap. HANDOFF 17.5 says a configured cap starting at 8; the Branch C plan removed it. Recommendation: a cap of 20 plus the existing repeat detection, recorded in `docs/decisions/`. |
| N2 | NX 2506 checks: the reflected `NewFaceProperties` and `NewMassProperties` overloads, whether the WinForms timer runs on NX's UI thread, what `UI.LockAccess` guarantees. Needs a recorded journal. |
| N3 | pi on Windows: version, `--print --mode json` event shape, quoting through `cmd.exe /d /c pi.cmd`. |
| N4 | Rule 7 and the flexibility goal. Section 4.6. |

## 4. Plan: flexible operations through pi planning, API lookup and a C# pipeline

### 4.1 Target flow

```
user request
  -> pi plans: OperationPlan (goal, entities, ordered steps, units)      [LLM, schema-checked]
  -> API lookup per step: NXOpen candidates with exact NX 2506 signatures [deterministic, read-only]
  -> binding: each step is bound to an operation the bridge can run       [deterministic]
       a. a compiled typed adapter (e.g. extrude, hole, edit_expression)
       b. a generic builder step over an allowlisted NXOpen builder (4.4)
       c. no binding: a gap report naming the missing API (4.5)
  -> pi fills arguments only from IDs and values that code produced       [LLM selects; rule 3]
  -> pipeline check: handles current, numbers grounded, units, kinds      [deterministic]
  -> preview of the whole pipeline in the panel, target highlighted       [human confirms]
  -> bridge runs the pipeline on NX's main thread under one undo mark;
     on any failure it rolls back to that mark                            [C#]
  -> typed results -> number checker -> answer
```

The LLM decides what to do and in which order. Code decides what can run and
checks every value. NX code that runs was compiled from the repository, not
written by the model.

### 4.2 Planning with pi

- pi returns an `OperationPlan` under a strict JSON schema in place of today's
  one-step heuristic plan. Python rejects plans that name unknown operations
  or entities.
- Keep a short deterministic safety pass. A plan that changes a part and is
  missing a target, a value or a unit triggers clarification. The questions
  come from the bound operation's schema ("which face?", "what diameter?"),
  not from verb lists. That fixes S12 and works in any language.
- The pending plan and its open questions are stored in the session. The next
  user message fills them in instead of starting over (C8).
- If a step fails, the runner tries the next validated binding for that step,
  then asks pi to replan with the failure attached. It stops when candidates
  run out, when the same step repeats, or at the round cap (N1).

### 4.3 One bridge, many operations: the capability manifest

- Merge `BranchCSmokeRuntime.cs` and `NxBridgeEntry.cs` into one assembly with
  these parts:
  - transport: TCP, token, `System.Text.Json`;
  - the main-thread queue with a time budget per tick;
  - a handle table;
  - an `IOperation` interface: `{Name, Kind, Version, ArgsSchema, ResultSchema, NxApis, Preview, Execute}`;
  - a `ChangeController` that sets the undo mark, runs the handler, rolls back
    on failure and refuses to save unless the operation is `save`.
- A `capabilities` read command returns the manifest. `ToolRegistry` builds
  its tool list from it, so the LLM sees only what this NX session can run
  (C4).
- Adding an operation then takes one C# `IOperation` class, one recorded
  journal and one test. There are no Python, prompt, skill or `FakeHarness`
  edits. Today the same change touches about 7 places (S7).
- Grow the adapter set in this order: measurements (length, radius, diameter,
  distance, angle, mass properties, bounding box), `list`, expressions and
  attributes, feature builders (extrude, revolve, hole, blend, chamfer, boolean,
  pattern), display and view, then drawing and export (FR-24).

### 4.4 Generic builder steps

Most NXOpen modelling follows one pattern:
`Create*Builder` -> set properties -> `Commit` -> `Destroy`. A single C#
operation `run_builder` can serve many features from data:

```json
{"op": "run_builder",
 "builder": "NXOpen.Features.ExtrudeBuilder",
 "set": {"Distance": 25.0, "Section": "$step1.section", "BooleanOperation.Type": "Subtract"},
 "targets": {"body": "h:3f2a:17:4"}}
```

- The bridge accepts only builder types on an allowlist and property paths read
  from the NXOpen 2506 assembly metadata. It checks value types, enums and
  units, and resolves `$stepN` references and handles itself. Nothing is
  compiled and nothing outside the allowlist can be reached.
- It reuses the change controller: one undo mark, rollback on error, no save.
- This is the main lever for flexibility. A new feature type is mostly an
  allowlist entry plus a recorded journal that confirms the property paths.
- Rule 7 status: the model writes no code, but it does choose which NXOpen
  builder and which properties are used. Record this as a decision before
  building it (4.6).

### 4.5 API lookup that pi can rely on

- Build the catalog on the Windows seat from the installed
  `NXBIN\managed\NXOpen*.dll` through .NET reflection (a `describe_api` read
  command or a build step). Signatures, enums and builder properties then match
  NX 2506 exactly. Keep the existing TSV and HTML index for summaries and
  synonyms.
- Add verified examples: recorded journals under `nx_bridge/recorded/` linked
  to the API members they use. pi gets a real call sequence as evidence, not
  just a name.
- Each candidate carries `bound_to`: the adapter or allowlisted builder that
  implements it, or nothing. A binding is "validated" only when that link
  exists. The current substring check (`api_search.py:175-200`) becomes
  ranking only.
- A step with no binding produces a gap report ("needs
  `NXOpen.Features.ThickenBuilder`; record a journal"). These are logged and
  counted, so the most requested missing operations become the next adapters
  to build. This replaces the post-MVP "high-frequency API" analysis with a
  concrete backlog.

### 4.6 Model-written C#: owner decision required (rule 7)

All three reviewers agree that running model-written NXOpen C# inside NX
violates rule 7 as written, even if it is compiled first. The options:

| Option | What pi produces | Executes in NX | Rule 7 |
|---|---|---|---|
| A. Typed adapters (4.3) | adapter IDs and arguments | repository code only | Compliant |
| B. Generic builder steps (4.4) | builder type and property values (data) | repository code with data from the model | Compliant in letter; record a decision |
| C. Draft and promote | C# adapter source written to `nx_bridge/candidates/` | nothing, until a person reviews it, CI builds it and a journal is recorded; then it becomes an A adapter | Needs a wording change ("never runs unreviewed model-written code") |
| D. Runtime-generated C# | a full C# pipeline per request | compiled and loaded into NX on each request | Needs rule 7 removed for this path |

Recommendation: build A and B for execution, and C as the authoring loop. pi
then does "form an NXOpen C# pipeline". It assembles pipelines from adapters
and builder steps at runtime, and writes new adapter source that a person
reviews and merges. Coverage grows without any unreviewed code running in
the user's NX session.

If D is chosen anyway, the minimum controls are:

- compile in a separate process against a fixed NXOpen reference set;
- reject at compile time any use of reflection, `System.IO`,
  `System.Diagnostics.Process`, networking, `Assembly.Load` or `Save`;
- show the user the full source in the panel and confirm it;
- run in a collectible `AssemblyLoadContext` on the main thread with a time
  limit and one undo mark, rolling back on error;
- never replay after a timeout;
- log the full source, its hash and the model name.

These controls lower the risk but cannot sandbox code running inside NX,
which keeps full file and session access.

## 5. Architecture changes

### 5.1 Layers (target)

```
browser panel (view only)  <-- WebSocket -->  assistant service (Python, long-running)
                                                 session store: conversation, pending plan, pending confirmation
                                                 planner (pi via HarnessAdapter), API catalog, binder, pipeline checker
                                                 ToolRegistry built from bridge capabilities
                                                 number checker, session log
                                           <-- loopback TCP + token -->
                                              nx_bridge (one C# assembly in NX)
                                                 main-thread queue, handle table, ChangeController
                                                 IOperation adapters, run_builder, capabilities, describe_api
```

### 5.2 Assistant service in place of a CLI process per message

- Replace `tools/branch_c_ui_server.py` shelling out to
  `uv run drawgen assistant chat --yes` with an in-process service. Use the
  standard library HTTP server or one small dependency (decision needed).
- The service keeps one agent per session, so clarification works across
  messages and the log is per conversation (C8, S8). It also removes the
  `uv` start-up delay on every message.
- A change request sends `{preview, confirm_id}` to the page. Only a click
  that returns that `confirm_id` continues (C1). Check `Origin` and use a
  per-launch token (S11).
- Make the browser the single panel and record A9. The Tk panel can stay as a
  test client.

### 5.3 Harness

- Run pi in a long-lived JSON or RPC mode if the installed version supports
  it, not one process per loop step. Add cancellation.
- Add record and replay traces of real pi sessions as CI fixtures (decision
  014).
- Move task recipes out of `_system_prompt` (`harness.py:27-53`) into each
  operation's manifest description, so the prompt grows with the manifest
  instead of being edited by hand.

## 6. Windows-specific items

- Hard-coded paths: `D:\codes\modeling_assistant` in
  `BranchCSmokeJournal.cs:15`, `BranchCSmokeLauncher.cs:18` and
  `BranchCSmokeRuntime.cs:47`; a user-profile path in `api_search.py:15`.
  Pass the repository root to NX through an environment variable set by the
  launcher, and read all paths from one settings source.
- `tools/build_branch_c.ps1` runs `dotnet build --no-restore`, so a clean
  checkout fails on the first build. Restore first.
- The csproj references `NXBIN\managed`, while `check_branch_c_journal.ps1`
  references `NXBIN\managed_core`. Confirm which is right on NX 2506 (N2).
- `DRAWGEN_CREATE_FIXTURE=explicit` is set in the launcher and inherited by
  NX, so the fixture part is created and saved on every launch (S10).
- The launcher assumes `msedge.exe` and the `pi.cmd` npm shim. Detect them, or
  read them from configuration.
- Write the endpoint file under `%LOCALAPPDATA%\drawgen` with a user-only ACL
  (S5).
- `cli.main` already switches stdout and stderr to UTF-8; keep that for the
  service. The C# side should use `System.Text.Json` with UTF-8 everywhere (S6).

## 7. Roadmap

Each phase ends with `make check` and the listed evidence.

| Phase | Work | Done when |
|---|---|---|
| R0 Safety | C1, C2, C5 (handle check only), C6, C7; S10, S11 | Tests: no confirmation means no change (per change tool); `changed` without a mark is rejected; an ungrounded numeric argument is rejected; timeout gives `outcome_unknown` |
| R1 One bridge | Merged C# assembly with main-thread queue, handle table, `ChangeController`, `System.Text.Json`, `capabilities`; registry filtered by it (C3, C4, S6, S7) | Seat recording shows one Undo per operation; shared protocol fixtures pass in Python and C# |
| R2 Assistant service | Long-running service, session store, browser preview and confirm, full logging (C8, S2, S8) | A clarification answered in the browser completes the original request; one log per conversation |
| R3 Pipelines | pi `OperationPlan` under a schema, binder, pipeline checker, runner with rollback and replanning; expand adapters (4.3 order) (S1, S12) | Eval set of multi-step requests (for example "extrude this sketch 20 mm and add a 2 mm blend") passes against the mock and on the seat |
| R4 API catalog | Reflection-built NX 2506 catalog, recorded-journal evidence, `bound_to` links, gap reports | Every plan step shows a binding or a gap report |
| R5 Builder steps | `run_builder` with allowlist, if decision 4.6-B is accepted | Each allowlisted builder has a recorded journal and an Undo test |
| R6 Authoring loop | pi drafts adapter source for gap reports, if option C is accepted | One promoted adapter goes from gap report to merged C# with review and recording |

## 8. Decisions needed from the owner

1. Rule 7 scope for flexibility: options A to D in 4.6. Recommendation: A + B,
   then C.
2. Round cap (N1): recommend 20 plus repeat detection.
3. Panel: the browser as the single panel, served by the assistant service (A9).
4. Data leaving the machine through pi or OpenAI (A12): part names, attribute
   text, measured values.
5. Geometry creation in scope (A10), since `create_box_with_hole` already
   exists and feature builders are the core of 4.3 and 4.4.
6. The NX 2506 seat checks in N2 and N3, recorded in
   `docs/nx_api_assumptions.md`.
