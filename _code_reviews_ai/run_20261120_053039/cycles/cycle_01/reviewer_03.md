# Reviewer 03 report

Review target `d3923a8` on top of `991fdb1`.

The implementation is a closed-demo skeleton for selection and two measurements, but it is far from the stated flexibility goal. The live path currently exposes a fixed registry, the API catalog is advisory metadata, and no typed pipeline is composed or executed. Several required safety guarantees are absent in the browser path and in both C# dispatch paths.

NX and PowerShell were not available in this review environment. Claims about the installed NX 2506 API surface, NX UI-thread behavior, and Windows ACL inheritance therefore remain marked as needs confirmation where appropriate.

## MUST_FIX

### 1. The browser UI bypasses the required confirmation gate

`tools/start_branch_c_ui.ps1:19` sets `DRAWGEN_UI_AUTO_CONFIRM` to `1`. The server defaults the flag to true and appends `--yes` to every browser chat command at `tools/branch_c_ui_server.py:98-100`. The browser page renders only the final answer at `web/branch_c_chat.html:93-100`. It has no preview, tool-call display, confirmation control, or pending confirmation state.

This lets a model-issued `change` call, including `save`, execute without an explicit confirmation in the panel. It directly violates HANDOFF 17.6 and rule 8. The CLI and Tk panel confirmation paths do not protect the browser path.

### 2. Change operations do not establish real undo marks before modification

The typed change tool path only creates a text preview at `src/drawgen/assistant/tools/__init__.py:365-374`. It does not highlight the target, and it does not validate the bridge result against the `changed` and `undo_mark` contract.

Both NX implementations modify state without the required mark. `BranchCSmokeRuntime.CreateBoxWithHole` calls `NewDisplay`, commits the block, and commits the cylinder at `nx_bridge/src/BranchCSmokeRuntime.cs:293-356`, then returns `changed: true` with `undo_mark: null` at `nx_bridge/src/BranchCSmokeRuntime.cs:369-375`. Its display path returns the literal `branch_c_display` at `nx_bridge/src/BranchCSmokeRuntime.cs:623-646` without calling `SetUndoMark`. The compiled dispatcher has the same defects. It returns the literal `branch_c` for display operations at `nx_bridge/src/NxBridgeEntry.cs:322-344` and returns `undo_mark: null` for box creation at `nx_bridge/src/NxBridgeEntry.cs:352-433`. Only `update` calls `SetUndoMark`, and it returns a label rather than the actual mark identifier at `nx_bridge/src/NxBridgeEntry.cs:436-440` and `nx_bridge/src/BranchCSmokeRuntime.cs:278-282`.

The result shown to the user can therefore claim that one Undo will revert a change when no corresponding mark was created. This is a direct rule 8 failure.

### 3. The compiled bridge dispatches NXOpen work from listener tasks

`BridgeServer.HandleClientAsync` invokes `_dispatcher.Dispatch` directly from the async listener task at `nx_bridge/src/BridgeServer.cs:51-79`. `InteractiveNxDispatcher.Dispatch` then reads and mutates NX state at `nx_bridge/src/NxBridgeEntry.cs:38-74`. There is no queue or main-thread callback in this dispatcher. Calling `_ui.LockAccess()` does not satisfy the stated contract that listener threads only queue work.

The smoke runtime has a different queue through `ProcessPendingRequests` at `nx_bridge/src/BranchCSmokeRuntime.cs:217-251`, so the two bridge implementations have materially different thread behavior. The loaded journal and the add-in form cannot be treated as equivalent until the compiled path uses the same main-thread dispatcher.

### 4. Timeout handling does not provide the required outcome-unknown behavior

The Python client applies a socket timeout at `src/drawgen/backends/bridge.py:37-59`, but it converts a timeout into the generic `bridge connection failed` error at `src/drawgen/backends/bridge.py:57-58`. The C# server never reads `options.timeout_s` and performs the whole dispatcher call before writing a response at `nx_bridge/src/BridgeServer.cs:63-79`. The smoke runtime has the same unbounded dispatch at `nx_bridge/src/BranchCSmokeRuntime.cs:245-259`.

Closing the client socket does not cancel an NX operation already running on the bridge. A change can complete after the client reports failure, and a user retry can apply it twice. HANDOFF 17.2 requires a distinct outcome-unknown result for a timed-out change and an agent prompt to inspect NX. There is no such state or response here.

The client does avoid an automatic replay, which is the one part of this timeout rule that is present.

### 5. The LLM-visible tool registry advertises commands that neither dispatcher implements

The registry exposes `open_part`, `switch_part`, `orient_view`, `list`, `edit_attribute`, `edit_expression`, and the drawing/export commands at `src/drawgen/assistant/tools/__init__.py:269-349`. The smoke dispatcher supports only the commands in `nx_bridge/src/BranchCSmokeRuntime.cs:264-290`. The compiled dispatcher has the same limited switch at `nx_bridge/src/NxBridgeEntry.cs:49-68`.

The model can therefore select tools that always return `unsupported NX command`. The registry has no capability handshake and no filtering based on the loaded bridge. This fails audit item 4 and prevents the advertised operation set from being reliable.

### 6. Clarification state is discarded between turns, especially in the browser path

`AssistantAgent.run` builds a new plan from only the current `user_message` at `src/drawgen/assistant/agent.py:38-49`. A clarification response is returned without being stored as an assistant question or pending plan. The browser server starts a fresh `drawgen assistant chat` process for every POST at `tools/branch_c_ui_server.py:74-86`, so it also creates a fresh agent and session log for every message.

The follow-up answer to a clarification cannot be merged with the original request. A request such as `Create a box` is classified as simple and gets no clarification at `src/drawgen/assistant/planning.py:43-58` and `src/drawgen/assistant/planning.py:61-74`, while the bridge silently supplies default dimensions at `src/drawgen/assistant/tools/__init__.py:72-95` and `nx_bridge/src/BranchCSmokeRuntime.cs:293-307`. This is unsafe for an operation that changes NX.

### 7. API discovery is not connected to execution, and the pipeline contract is unused

`discover_api_candidates` only attaches catalog IDs and assumptions to an `OperationPlan` at `src/drawgen/assistant/planning.py:125-164`. The agent passes that plan to the harness and then calls `ToolRegistry.execute` directly at `src/drawgen/assistant/agent.py:56-110`. No code constructs or executes `PipelineStep` or `PipelineResult`, despite their declarations in `src/drawgen/contracts/operation_plan.py:63-101`.

The catalog validator only performs lexical term checks at `src/drawgen/assistant/api_search.py:175-200`. The agent does not supply an NX version, so candidates are marked validated with `nx_version: null`. No candidate is probed against NX, mapped to a typed adapter, or required by a tool call. This means the core owner goal of plan, API lookup, and pipeline composition is not implemented. The system can only run the handful of hard-coded adapters that happen to exist.

### 8. The number checker does not implement the required rounding, count, or tool-argument rules

`check_answer` compares raw floating-point tokens with a fixed `1e-9` tolerance at `src/drawgen/assistant/checker.py:30-38`. It does not compare at the decimals displayed in the answer and does not derive counts from list lengths. It also scans every numeric token in arbitrary metadata, handles, and paths at `src/drawgen/assistant/checker.py:12-27`.

The offline check `check_answer("Area is 1.23 mm2", [{"value": 1.234}])` returns false, although 1.23 is the displayed-precision rounding of 1.234. `check_answer("There are 2 faces", [{"items": [{}, {}]}])` also returns false because it never counts the list. Conversely, numbers in tags or unrelated result fields can satisfy the raw-token match.

No code checks numeric provenance for tool arguments. `ToolRegistry.execute` validates only the Pydantic type and dimensions at `src/drawgen/assistant/tools/__init__.py:354-379`. The offline check accepted a confirmed `create_box_with_hole` call with width `999` even when that number was absent from the user message and prior tool results. This violates HANDOFF 17.5 and permits ungrounded model-supplied edit values.

### 9. Handles are raw NX tags with no session generation or invalidation

Both C# implementations issue `tag:<uint>` handles at `nx_bridge/src/BranchCSmokeRuntime.cs:650-668` and `nx_bridge/src/NxBridgeEntry.cs:451-469`, then resolve them globally through `NXObjectManager.GetObjectFromUInt`. There is no bridge-owned handle table, session ID, part/context generation, or check that the object belongs to the current work/displayed part. `PartRef` also reports `modified: false` unconditionally at `nx_bridge/src/BranchCSmokeRuntime.cs:394-402` and `nx_bridge/src/NxBridgeEntry.cs:91-95`.

After opening, switching, or creating a part, an old tag can remain resolvable or be reused for a different object. The tool layer accepts any string handle and never invalidates cached results. This violates the session-local handle requirement and can apply a display or edit command to the wrong object.

## SHOULD_FIX_IMPORTANT

### 10. The bridge has no single-client or request-size discipline, and the smoke queue drains without slices

Both servers accept multiple clients with the same token. `BridgeServer.AcceptLoopAsync` starts an independent handler for each client at `nx_bridge/src/BridgeServer.cs:40-48`, and the smoke listener does the same at `nx_bridge/src/BranchCSmokeRuntime.cs:175-190`. The bridge protocol assumes one client per session but does not enforce it.

The smoke queue reads an unbounded line with `ReadLine` at `nx_bridge/src/BranchCSmokeRuntime.cs:193-209`, and `ProcessPendingRequests` drains the entire queue in one UI-timer callback at `nx_bridge/src/BranchCSmokeRuntime.cs:217-226`. A slow or oversized request can hold a listener thread, and a burst of work can block NX input for an unbounded interval. Add bounded framing, cancellation or rejection, and a short-slice scheduler before relying on the bridge for interactive NX.

The smoke runtime also extracts request fields with regular expressions at `nx_bridge/src/BranchCSmokeRuntime.cs:672-688` and parses measurements with an order-sensitive regular expression at `nx_bridge/src/BranchCSmokeRuntime.cs:451-483`. It does not validate the protocol field or parse arbitrary valid JSON. A semantically valid request with reordered fields can produce an empty successful measurement result.

Both bridge paths do echo a request ID in their normal response path, and the Python client checks that echo at `src/drawgen/backends/bridge.py:63-67`. That check cannot distinguish a late response from a timed-out request because the client closes the connection and discards the request state.

### 11. Session logs do not meet the required event and provenance contract

`SessionLog` writes only a timestamp, event name, and arbitrary payload at `src/drawgen/assistant/log.py:12-21`. The agent records user messages, plans, harness requests, steps, tool results, and checker events at `src/drawgen/assistant/agent.py:38-43` and `src/drawgen/assistant/agent.py:64-128`, but it never records a confirmation event, a separate tool-call event, model name, or prompt hash. The browser creates a new random session for each POST because it does not pass `--session` at `tools/branch_c_ui_server.py:74-86`.

This prevents an end-to-end audit of confirmation and model decisions and breaks the one-log-per-conversation requirement in the browser UI.

### 12. The result and capability contracts are too loose for a typed pipeline

`ToolSpec` contains only name, kind, description, and `args_schema` at `src/drawgen/assistant/contracts.py:45-50`. It has no result schema or adapter/API candidate reference. `OperationResult` permits `changed: true` with a null undo mark at `src/drawgen/contracts/live.py:111-116`, and the registry accepts the bridge result without enforcing invariants at `src/drawgen/assistant/tools/__init__.py:375-384`.

Adding one new operation currently requires a Pydantic args class, a registry tuple entry, a Python command mapping, a branch in `BranchCSmokeRuntime.Dispatch`, a second branch in `NxBridgeEntry.Dispatch`, and usually duplicated C# implementation code. The duplicate dispatchers make it easy for the loaded journal and add-in to diverge, as they already do for command support and thread dispatch.

### 13. The agent turn has no configured round limit or bounded invalid-call retry

`AssistantAgent.run` loops forever at `src/drawgen/assistant/agent.py:55-66`. It does not implement the HANDOFF limit of at most a configured number of rounds, and an invalid tool or argument returns immediately instead of using the required bounded retry path at `src/drawgen/assistant/agent.py:101-104`. The test `tests/unit/assistant/test_assistant.py:129-142` explicitly requires nine tool rounds, confirming that the implementation removed the specified bound.

A harness that keeps emitting distinct calls can hold the NX session and browser request until the outer 180-second process timeout. A malformed or unknown call also receives no repair attempt. Add a configured per-turn budget and bounded schema-error retries before executing more tools.

### 14. Windows build and launch scripts depend on machine-specific paths and skip restore

The journal loader and launcher hard-code `D:\codes\modeling_assistant` at `nx_bridge/BranchCSmokeJournal.cs:14-20` and `nx_bridge/BranchCSmokeLauncher.cs:16-22`. The smoke runtime hard-codes the same work root at `nx_bridge/src/BranchCSmokeRuntime.cs:47-50` and `nx_bridge/src/BranchCSmokeRuntime.cs:309-314`. The scripts default to `D:\softwares\NX2506` at `tools/build_branch_c.ps1:1-8` and `tools/start_branch_c_ui.ps1:1-3`.

`build_branch_c.ps1` invokes `dotnet build --no-restore` at `tools/build_branch_c.ps1:17-21`, but no `obj/project.assets.json` is part of the repository. A clean seat therefore has no reliable first-build path. The journal type checker references `NXBIN\managed_core` at `tools/check_branch_c_journal.ps1:29-31`, while the project references `NXBIN\managed` at `nx_bridge/NxBridge.csproj:12-26`. The exact NX 2506 directory layout needs a seat check, but the two scripts currently do not agree.

### 15. The UI does not expose the tool calls, results, or undo note required by the panel contract

The Tk panel appends only `answer` and `ask_user` text at `src/drawgen/assistant/panel/app.py:63-81`. The browser does the same at `web/branch_c_chat.html:93-100`. Neither path renders each tool call with arguments, the returned result, the undo mark, or the required note that one Undo in NX reverts the change. This makes it impossible for a user to inspect what will happen before confirmation even where the CLI confirmation callback is used.

## NEEDS_CONFIRMATION

### 16. The NX 2506 API calls and UI dispatch assumptions need a real seat recording

The C# code reflects `MeasureManager.NewFaceProperties` and `NewMassProperties` at `nx_bridge/src/BranchCSmokeRuntime.cs:242-318` and `nx_bridge/src/NxBridgeEntry.cs:242-318`, and it uses `UI.LockAccess` as part of dispatch at `nx_bridge/src/NxBridgeEntry.cs:49-73`. These calls are not listed in `docs/nx_api_assumptions.md`, and no NX 2506 build or journal run was possible here. Confirm the signatures, units, disposal behavior, and whether the timer callback is actually NX's main thread before treating the measurement and smoke paths as working.

### 17. Endpoint-file permissions and host validation are not established

The smoke runtime writes the token endpoint with ordinary `File.WriteAllText` at `nx_bridge/src/BranchCSmokeRuntime.cs:56-67`. The compiled entry point does the same at `nx_bridge/src/NxBridgeEntry.cs:23-33`. Neither path sets an ACL restricting the file to the current Windows user. `BridgeBackend` also trusts the `host` field from the endpoint file at `src/drawgen/backends/bridge.py:30-35` instead of enforcing loopback.

Windows inherited ACLs and the actual location of `%LOCALAPPDATA%` need confirmation on the seat. The implementation should still explicitly create a user-only endpoint file and reject non-loopback hosts to make the protocol invariant enforceable.

### 18. The Pi command line and `.cmd` shim behavior need seat validation

The PowerShell launcher chooses `pi.cmd` and `--print --mode json` at `tools/start_branch_c_ui.ps1:16-18`. The adapter does wrap `.cmd` files through `cmd.exe /d /c` on Windows at `src/drawgen/assistant/harness.py:316-321` and forces UTF-8 capture at `src/drawgen/assistant/harness.py:323-330`, which is directionally correct. The repository does not pin the pi version or record its actual JSON contract, cancellation behavior, or authentication/session semantics. The selected pi distribution must be checked on the Windows seat before relying on this invocation.

## Design input for the flexibility goal

Rule 7 is binding for this review. A model-generated C# file or journal compiled and run inside NX would directly violate the rule, even if the compiler were invoked from a local process. It also creates an execution boundary that would need code signing, reference allowlists, compiler isolation, resource limits, cancellation, API-version checks, and a transaction-level undo and save policy. Those controls would reduce risk but would not make model-written NXOpen execution compliant with the current rule.

The compliant path is a versioned set of pre-compiled, typed NX adapters. The model can plan a sequence of adapter IDs, use a read-only catalog to select candidate APIs, and form a `PipelineStep` list whose arguments are validated against user-provided values, current-session handles, and adapter schemas. A deterministic pipeline runner can execute only those IDs through one shared main-thread bridge dispatcher. Each adapter should declare its read/session/change kind, preview builder, target-handle requirements, undo behavior, result contract, supported NX versions, and whether it may save. The bridge should reject an adapter or candidate that is absent from the loaded capability manifest.

This design reaches broad operation coverage by adding compiled adapters and catalog evidence without allowing the model to author executable NXOpen code. The current implementation needs the pipeline runner, capability handshake, shared dispatcher, session handle generation, and confirmation state before that design can be evaluated on the NX seat.

## Test coverage gap

The current tests cover basic fake measurements, one CLI-style confirmation callback, and a happy-path fake bridge. They do not cover browser no-confirmation-no-change, real or fake undo-mark invariants, stale handles after a part change, bridge timeouts with a late mutation, main-thread dispatch, unsupported tool filtering, argument-number provenance, rounding and counts, endpoint ACLs, or the C# dispatchers. The loopback test in `tests/unit/backends/test_live.py:39-72` could not bind a socket in this macOS sandbox. The targeted offline run otherwise reported 23 passing tests and this environment failure.
