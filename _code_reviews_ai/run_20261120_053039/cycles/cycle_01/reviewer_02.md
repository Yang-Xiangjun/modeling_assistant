# Reviewer 02 report

## Scope and validation

This review covers commit `d3923a8` on top of `991fdb1`, with the Branch C files named in the review scope and the requirements in `CLAUDE.md`, `HANDOFF.md` sections 17.2 through 17.7, the Branch C implementation plan, and decision 014.

`UV_CACHE_DIR=.uv-cache make gate` passed. It reported Ruff, formatting, strict mypy, the Python 3.10 pass, and 112 architecture tests as passing. The selected assistant and live-backend tests produced 23 passes. The socket round-trip test could not bind a local socket in this review sandbox, so that one result is environmental. NX, the NXOpen assemblies, .NET, and PowerShell are unavailable here. Claims about seat behavior are marked `NEEDS_CONFIRMATION`.

The implementation is a useful offline typed-tool prototype, but it is materially short of the stated flexibility goal. The planning and API-search objects are passed to the harness, while no typed pipeline is composed or executed. The live implementation is also unsafe for the required change path until main-thread dispatch, confirmation, undo marks, and handle lifetime are corrected.

The following controls are present in the code. Both C# listeners bind `TcpListener` to loopback, compare the request token, and echo the request ID. `BridgeBackend` generates a fresh request ID, checks the echoed ID, and has no automatic retry. Existing tool schemas contain no NXOpen source, journal, shell command, or executable-path field. `SessionLog` writes local JSONL events. These controls reduce the attack and replay surface, but they do not compensate for the main-thread, lifetime, and browser confirmation defects below.

## Findings

### MUST_FIX-01. The compiled dispatcher does not marshal NXOpen to the NX main thread

`BridgeServer.HandleClientAsync` invokes `_dispatcher.Dispatch` directly after reading the socket request at `nx_bridge/src/BridgeServer.cs:63-70`. `InteractiveNxDispatcher.Dispatch` then performs NXOpen work under `_ui.LockAccess()` at `nx_bridge/src/NxBridgeEntry.cs:49-73`. There is no queue or NX main-thread callback in this path. Concurrent client tasks can therefore enter NXOpen from thread-pool continuations, with no code-level guarantee that calls run on NX's main thread.

This violates HANDOFF 17.2 and can make NX calls race with the UI. The smoke journal has a separate queue and timer at `nx_bridge/src/BranchCSmokeRuntime.cs:175-226`, but that does not repair the compiled dispatcher. The two bridge implementations have different threading guarantees and must not be treated as interchangeable.

### MUST_FIX-02. Changing commands do not create and return a real undo mark

The C# display path mutates the object before returning the literal string `"branch_c"` at `nx_bridge/src/NxBridgeEntry.cs:322-344`. `CreateBoxWithHole` commits two features and returns `undo_mark = null` at `nx_bridge/src/NxBridgeEntry.cs:352-433`. `Update` creates a mark but discards the returned `Session.UndoMarkId` and returns the label `"branch_c_update"` at `nx_bridge/src/NxBridgeEntry.cs:436-440`. The journal runtime repeats the same behavior at `nx_bridge/src/BranchCSmokeRuntime.cs:264-290`, `293-377`, and `642-647`.

The Python registry only produces a preview and then forwards the command at `src/drawgen/assistant/tools/__init__.py:354-384`. The mock backend invents an undo mark for every call at `src/drawgen/backends/live_mock.py:69-83`, so the current tests can pass while the loaded bridge violates rule 8 and NFR-14. A real mark must be created immediately before the first modification, its actual returned identifier must be included in the result, and the operation must have one mark per change call.

### MUST_FIX-03. The browser path bypasses the required panel confirmation

The browser launcher sets `DRAWGEN_UI_AUTO_CONFIRM = '1'` at `tools/start_branch_c_ui.ps1:19`. The server defaults the same flag to true at `tools/branch_c_ui_server.py:67` and appends `--yes` to every chat command at `tools/branch_c_ui_server.py:98-99`. The CLI interprets `--yes` as unconditional confirmation at `src/drawgen/cli.py:102-109`.

The HTML page has only a send button and transcript at `web/branch_c_chat.html:93-104`. It has no preview card, confirmation control, or confirmation request identifier. A change sent through the documented browser startup therefore executes without an explicit user confirmation in the panel, contrary to HANDOFF 17.6 and rule 8. This is a safety defect even though direct terminal use can prompt.

### MUST_FIX-04. The handles are global NX tags rather than session-local handles

Both C# implementations issue `tag:<Tag>` handles at `nx_bridge/src/NxBridgeEntry.cs:461` and `nx_bridge/src/BranchCSmokeRuntime.cs:660`. Both resolve an arbitrary tag through `NXObjectManager.GetObjectFromUInt` at `NxBridgeEntry.cs:463-470` and `BranchCSmokeRuntime.cs:662-669`. There is no bridge-owned handle table, session identifier, part/context generation, or invalidation after a part switch or creation of a new active part.

A handle returned before a context change can therefore be submitted later, and a caller can submit a guessed tag that happens to resolve. This violates the session-handle contract in HANDOFF 17.3 and makes a later change capable of targeting a stale or unintended object. The target must be resolved only through a bridge-issued, session-scoped entry whose lifetime is tied to the current part/context.

### MUST_FIX-05. The advertised tool set is not implemented by either loaded dispatcher

`ToolRegistry._register_defaults` advertises `open_part`, `switch_part`, `orient_view`, `edit_attribute`, `edit_expression`, all drawing commands, and `update_views` at `src/drawgen/assistant/tools/__init__.py:269-349`. The compiled dispatcher switch at `nx_bridge/src/NxBridgeEntry.cs:54-67` implements neither those commands nor `list`. The journal dispatcher at `nx_bridge/src/BranchCSmokeRuntime.cs:264-290` is smaller still. A request can pass Python argument validation and reach `unsupported NX command` in the bridge.

The `measure` contract accepts length, radius, diameter, distance, and angle at `src/drawgen/contracts/live.py:70-78`, but both C# dispatchers implement only area and volume. The compiled `save` implementation also ignores the supplied part handle and always saves `_session.Parts.Work` at `nx_bridge/src/NxBridgeEntry.cs:443-448`. This makes the fixed list and the actual bridge capability inconsistent, blocks FR-22 through FR-24, and gives the harness an execution surface it cannot safely rely on. The two dispatchers duplicate command logic with different support and should be treated as one capability registry before more tools are exposed.

## SHOULD_FIX_IMPORTANT

### SHOULD_FIX_IMPORTANT-01. Planning and API evidence do not produce or constrain an executable pipeline

`build_operation_plan` always creates one heuristic `PlanStep` at `src/drawgen/assistant/planning.py:77-108`. `discover_api_candidates` searches one TSV catalog and marks a candidate validated after token matching at `src/drawgen/assistant/planning.py:125-163` and `src/drawgen/assistant/api_search.py:176-200`. It does not validate an NX2506 signature by a bridge probe, search verified journals or project API notes, or select an adapter.

`PipelineStep` and `PipelineResult` exist only as contracts in `src/drawgen/contracts/operation_plan.py:63-101`. There is no `assistant/pipeline.py`, no pipeline composer, and no pipeline execution path. `AssistantAgent` passes the plan to the harness at `src/drawgen/assistant/agent.py:41-63`, but a prompt instruction is the only enforcement that the model use API evidence. The `search_nx_api` tool returns candidates but the tool layer does not require a candidate ID before an operation.

Consequently pi can choose among the hard-coded typed tools, but it cannot look up an API and form an NXOpen C# pipeline for an operation outside those adapters. Failed calls immediately become an `ask_user` result at `agent.py:111-114`, so the planned candidate fallback and replanning loop are absent. This is the primary gap from the owner’s flexibility goal.

### SHOULD_FIX_IMPORTANT-02. Clarification state is lost across browser turns and is incomplete even in one agent process

`AssistantAgent.run` returns a clarification prompt before invoking the harness at `src/drawgen/assistant/agent.py:41-50`. It does not store a pending plan or append the generated question to the conversation. A subsequent call rebuilds a plan from only the new user message.

The browser server starts a new `drawgen assistant chat` subprocess for each POST at `tools/branch_c_ui_server.py:71-129`. It passes no session identifier, conversation, pending plan, or confirmation token. The documented browser path therefore cannot answer a clarification question in context, cannot resume a preview, and creates a new session log for every message. This fails the clarification and panel interaction requirements in FR-25 and FR-26.

### SHOULD_FIX_IMPORTANT-03. The number checker does not implement the required matching rule or tool-argument check

`check_answer` collects every numeric token recursively from `sources` and requires exact equality within `1e-9` at `src/drawgen/assistant/checker.py:9-37`. `sources` starts with the user message at `src/drawgen/assistant/agent.py:51` and later includes whole result objects at `agent.py:115-119`. That admits numbers from the request, handles, tags, paths, and metadata. It rejects displayed-precision rounding and has no count or unit-conversion logic. For example, the current function rejects `1.23` for a tool value of `1.234`, accepts `12` when it appears only in the user message, and can accept a count because the same number occurs in a tag.

The required argument rule is absent. `ToolRegistry.execute` validates types at `src/drawgen/assistant/tools/__init__.py:354-364`, but never checks that numeric tool arguments occur in the user conversation or a prior tool result. The scripted box harness can supply default dimensions that were not in the user message and the call is accepted. This affects NFR-12, the expression-edit safety rule, and the inspection-answer accuracy gate.

### SHOULD_FIX_IMPORTANT-04. Timeout handling can leave a change running with no outcome-unknown state

`BridgeBackend._request` times out the socket at `src/drawgen/backends/bridge.py:46-58`, then reports a generic connection failure. The C# bridge ignores `BridgeRequest.Options` and has no cancellation or deadline handling at `BridgeServer.cs:63-80` and `BranchCSmokeRuntime.cs:217-260`. A long NX operation can continue after Python closes the connection. A user retry can then run the same change twice, while the assistant has no explicit “outcome unknown” state required by HANDOFF 17.2.

The smoke runtime also drains its entire queue in one timer callback at `BranchCSmokeRuntime.cs:217-226`, so a long operation can block the NX UI. Seat testing must measure this, and the protocol needs a clear non-replay and unknown-outcome path for timed-out changes.

### SHOULD_FIX_IMPORTANT-05. The context and selection data do not meet the live contract

Both C# dispatchers hard-code `modified = false`, return `active_sheet = null`, and return `component_path = null` and `fingerprint = null` for every selection. See `nx_bridge/src/NxBridgeEntry.cs:76-95`, `97-153`, and `nx_bridge/src/BranchCSmokeRuntime.cs:379-448`. Selection properties are limited to tag, name, area, surface area, and volume.

This prevents stale-context detection, component targeting, fingerprint matching, and the required length/radius/diameter/distance/angle inspection operations. It also means the C3 unsaved-change check cannot rely on `SessionContext.modified`.

### SHOULD_FIX_IMPORTANT-06. Windows launchability depends on repository-specific absolute paths

The journal loader and launcher hard-code `D:\codes\modeling_assistant` at `nx_bridge/BranchCSmokeJournal.cs:14-20` and `nx_bridge/BranchCSmokeLauncher.cs:18-21`. The runtime uses the same path for work parts at `nx_bridge/src/BranchCSmokeRuntime.cs:47-50` and `309-313`, and the compiled dispatcher uses it at `nx_bridge/src/NxBridgeEntry.cs:368-373`. The PowerShell scripts compute `$repo`, but that value is not passed to the journal runtime.

The default NX path is also duplicated in the PowerShell scripts and README. A checkout at another drive or directory can build successfully and still fail when the journal is loaded. `build_branch_c.ps1` invokes `dotnet build --no-restore` at `tools/build_branch_c.ps1:17-21`, so a clean checkout without an existing assets file also depends on an unstated prior restore. The project references `NXBIN\managed`, while the journal checker references `NXBIN\managed_core` at `tools/check_branch_c_journal.ps1:29-31`. The existence and correct location of those NX 2506 assemblies need seat confirmation.

The smoke setup has an additional save side effect. `CreateFixture` calls `part.Save` at `nx_bridge/src/BranchCSmokeRuntime.cs:170-172`, and the normal UI launcher enables fixture creation by default at `tools/start_branch_c_ui.ps1:20-24`. This is test setup rather than an assistant change tool, but it should remain isolated from an existing user part because the project rule is that saving is explicit.

### SHOULD_FIX_IMPORTANT-07. Tests exercise the mock policy, not the bridge safety properties

The assistant tests assert confirmation and an undo-mark count against `MockLiveBackend` at `tests/unit/assistant/test_assistant.py:144-160`. That backend always appends a synthetic mark and does not model stale handles, main-thread dispatch, timeout continuation, or actual undo behavior. There are no C# tests, no bridge integration test for an unsupported command, no no-confirmation test through the browser route, no stale-handle test, no timeout outcome test, and no test that a numeric tool argument is rejected.

The offline gate passing is therefore not evidence for AC-10, NFR-14, NFR-15, or the main-thread requirement. The available live round-trip test covers only response parsing and could not bind a socket in this sandbox.

## SHOULD_FIX_MINOR

### SHOULD_FIX_MINOR-01. The preview is generic and does not perform the required target highlight

`ToolRegistry.execute` builds a string from the raw payload at `src/drawgen/assistant/tools/__init__.py:365-373`. It does not show target names, old and new values, or call `highlight_entity` before confirmation. The panel only displays that string through a message box at `src/drawgen/assistant/panel/app.py:40-45` and `67-71`. This falls short of the detailed preview and highlight steps in HANDOFF 17.6 even where the confirmation callback is present.

### SHOULD_FIX_MINOR-02. Tool specifications have argument schemas but no result schemas

`ToolSpec` contains only `name`, `kind`, `description`, and `args_schema` at `src/drawgen/assistant/contracts.py:45-49`. `ToolDefinition` similarly records no typed result model at `src/drawgen/assistant/tools/__init__.py:152-158`. The LLM and registry cannot validate command-specific result contracts before they are fed back into planning.

## NEEDS_CONFIRMATION

These points require the Windows NX seat and should not be treated as proven defects from this macOS review.

- The exact NX 2506 `NewMassProperties`, `NewFaceProperties`, body-array, unit, and `UI.LockAccess` behavior in `NxBridgeEntry.cs:242-319` must be compiled and exercised against the installed assemblies. Reflection makes the code tolerant of signatures but does not establish that the selected overload is correct.
- The smoke runtime’s `System.Windows.Forms.Timer` callback at `BranchCSmokeRuntime.cs:78-105` must be shown to execute on the NX UI thread under the hosted .NET 8 runtime. The compiled dispatcher currently has no equivalent queue.
- NX’s add-in/journal load mechanism, .NET 8 assembly load context, and whether `NXBIN\managed` or `NXBIN\managed_core` is the correct path must be verified on NX 2506.
- `NxBridgeEntry.Main` requires `DRAWGEN_BRIDGE_TOKEN` at `nx_bridge/src/NxBridgeEntry.cs:19-32`, while the provided PowerShell launch path does not set it. The smoke journal generates a token if absent at `BranchCSmokeRuntime.cs:56-67`. The intended production token provisioning and endpoint ACLs are unresolved.
- The installed pi version, stdin contract, `--print --mode json` flags, and `pi.cmd` invocation behavior are not established. They are configured at `src/drawgen/assistant/harness.py:283-346` and `tools/start_branch_c_ui.ps1:16-18`. The adapter does handle `.cmd` through `cmd.exe /d /c`, but that does not prove the flags or JSON event shape for the seat’s pi version.

## Flexibility goal and rule 7

Rule 7 is binding for the current code. The current skill explicitly tells pi to return typed tool calls and never write NXOpen code at `.pi-agent/skills/nxopen-cad/SKILL.md`. That keeps the closed-tool rule intact, but it means the owner’s open-ended goal is only possible within the precompiled capability surface.

The compatible design is a model-composed pipeline of precompiled typed adapters. The model can produce an `OperationPlan` containing ordered adapter IDs and typed arguments. API search can provide exact evidence and map a step to a versioned adapter. The bridge accepts only registered adapter IDs, validates the argument schema, checks session-scoped handles and current context, builds a preview, waits for panel confirmation, creates the undo mark on the NX main thread, executes one transaction, and returns the real mark and typed outputs. API evidence remains read-only and never becomes executable source. This preserves rule 7 and gives a clear extension unit. A new operation requires a typed adapter contract, one bridge implementation, registry metadata, a recorded NX 2506 validation, and tests for preview, confirmation, undo, timeout, and stale handles.

Model-generated C# compiled at runtime would offer broader API coverage, but it is disallowed by rule 7 because the executed program is model-written NXOpen. If the owner changes that rule, the minimum guardrails would include offline compilation before NX access, a fixed NXOpen reference and API allow-list, static rejection of reflection, dynamic loading, file and process access, network access, and save calls, typed input binding, a reviewed source and diff, a mandatory preview and confirmation, a per-session capability token, main-thread-only execution, resource and timeout limits, one undo transaction, no automatic replay after timeout, and complete audit logs. Even with those controls it would be a new security and governance decision, not an implementation detail.

## Overall assessment

The branch demonstrates the Python contracts, a provider-neutral harness shape, and a useful mock-driven measurement path. It does not yet provide a safe live change path or a flexible plan-to-pipeline architecture. The MUST_FIX findings should be resolved before any interactive NX operation is treated as production-capable. The owner must also choose whether flexibility means expanding the typed adapter registry under rule 7 or formally changing rule 7 to permit a separately governed runtime-code design.
