# Branch C review

Review target `d3923a8` on top of `991fdb1`. The checkout also contains the
follow-up lint-only commit `9c6406b`. The findings below are based on the
Branch C files and are unchanged by that formatting commit.

## Executive assessment

The MVP has a useful typed Python boundary, a loopback client, and a first
measurement/box vertical slice. It is still far from the owner's flexibility
goal. API search is planning metadata rather than an enforced selection or
pipeline mechanism, and the bridge only implements a small hard-coded subset
of the advertised tools. The current live path also has rule-8 and rule-7
blocking defects. The browser path auto-confirms changes, the add-in dispatcher
executes NXOpen from the listener thread, and the geometry/display changes do
not create real undo marks.

## MUST_FIX

### M1. Browser changes bypass explicit confirmation

`tools/branch_c_ui_server.py:98-100` appends `--yes` whenever
`DRAWGEN_UI_AUTO_CONFIRM` is true, and `_env_flag` defaults that setting to
true at `tools/branch_c_ui_server.py:21-25`. The launcher explicitly sets it to
`1` at `tools/start_branch_c_ui.ps1:19`. The browser has no confirmation
control or confirmation request in `web/branch_c_chat.html:93-102`.

Every browser change therefore reaches `AssistantAgent.run(..., --yes)` and is
executed without a panel confirmation. This directly violates rule 8 and
HANDOFF 17.6. The browser UI also shows only a generic “Pi is working” item
and the final answer, so the user cannot approve the specific operation.

### M2. Most C# change commands do not set a real undo mark

The typed tool layer promises an undo in its generic preview at
`src/drawgen/assistant/tools/__init__.py:365-373`, but both C# dispatchers
return fabricated or null marks for modifying operations.

- `nx_bridge/src/NxBridgeEntry.cs:322-344` returns the string `branch_c` from
  display changes without calling `SetUndoMark`.
- `nx_bridge/src/NxBridgeEntry.cs:352-433` creates the box and hole, modifies a
  new part, and returns `undo_mark = null`.
- `nx_bridge/src/BranchCSmokeRuntime.cs:623-647` has the same display problem,
  and `:293-376` returns a null mark for box creation.
- Among the command handlers, only update calls `SetUndoMark`, at
  `nx_bridge/src/NxBridgeEntry.cs:436-440` and
  `nx_bridge/src/BranchCSmokeRuntime.cs:278-282`, and those return the label
  rather than a verifiable mark identifier.

Consequently a confirmed `create_box_with_hole`, `show_entity`,
`hide_entity`, or `isolate_entity` cannot satisfy “one Undo in NX reverts it.”
The mock backend records marks, so the current Python tests do not exercise the
actual C# behavior.

The default smoke/manual-test path also sets `DRAWGEN_CREATE_FIXTURE=explicit`
(`tools/start_branch_c_manual_test.ps1:10-13` and
`tools/start_branch_c_ui.ps1:20-24`), and the journal fixture saves the part at
`nx_bridge/src/BranchCSmokeRuntime.cs:170-171`. Starting that path can therefore
modify and save NX state before a chat confirmation exists.

### M3. The compiled add-in calls NXOpen from a listener thread

`nx_bridge/src/BridgeServer.cs:64-72` invokes `_dispatcher.Dispatch` directly
inside `HandleClientAsync`, which is created by the asynchronous accept loop at
`:40-48`. `NxBridgeEntry.InteractiveNxDispatcher.Dispatch` then calls
`_ui.LockAccess()` and NXOpen operations directly at
`nx_bridge/src/NxBridgeEntry.cs:49-74`.

There is no queue to an NX main-thread callback in this path. `LockAccess` does
not establish the required main-thread dispatch. This violates HANDOFF 17.2
and can make NX calls race or fail when the add-in form is loaded.

The journal runtime has a queue and timer at
`nx_bridge/src/BranchCSmokeRuntime.cs:175-250`, but it drains the entire queue
in one timer callback at `:217-261` and does not enforce a short-slice budget.
Its timer and `UI.LockAccess` behavior still require seat validation.

### M4. The LLM tool list contains commands that neither bridge implements

The registry exposes `open_part`, `switch_part`, `orient_view`, all attribute
and expression edits, and the drawing/export tools at
`src/drawgen/assistant/tools/__init__.py:269-349`. It also exposes `list` as a
backend command at `:262-268`.

`NxBridgeEntry` dispatches only context, selection, measure,
`create_box_with_hole`, display, fit, update, and save at
`nx_bridge/src/NxBridgeEntry.cs:54-67`. The journal dispatcher has the same
small set at `nx_bridge/src/BranchCSmokeRuntime.cs:264-290`. There is no
`list`, open/switch, edit, drawing, or export implementation. A model can
select a listed tool and receive an unsupported-command error, which also
means the claimed extensibility is not present.

### M5. Number provenance and answer checking do not meet HANDOFF 17.5

HANDOFF 17.5 requires every number placed in a tool argument to occur in the
user conversation or a prior tool result. `AssistantAgent` only uses
`sources` for checking numbers in a final answer at
`src/drawgen/assistant/agent.py:51-53` and `:71-78`. It never checks numbers in
the tool arguments. `ToolRegistry.execute` validates types and ranges only at
`src/drawgen/assistant/tools/__init__.py:354-379`.

For example, a model can issue an `edit_expression` value or box dimensions
that were never stated by the user and were not returned by NX. This is a
direct 17.5 correctness gap, even though the arguments are typed.

The final-answer checker at `src/drawgen/assistant/checker.py:9-38` matches
numbers with an absolute `1e-9` tolerance. It does not implement the required
displayed-precision rounding. A result of `12.3456` therefore rejects the
legitimate displayed answer `12.35`. It also treats every numeric substring in
all nested result fields as an allowed number, including tags and durations,
and includes the original user message in `sources`, so a user-supplied number
can pass without any tool result. It does not validate derived counts or unit
conversions. On failure the agent
returns a generic sentence at `agent.py:76-78` instead of the required one-time
retry with the named checker failure.

### M6. Handles are raw tags with no session lifetime or invalidation

Both dispatchers issue `tag:<uint>` handles through `Handle` and resolve them
with `NXObjectManager.GetObjectFromUInt` at
`nx_bridge/src/NxBridgeEntry.cs:461-470` and
`nx_bridge/src/BranchCSmokeRuntime.cs:650-669`. There is no bridge-owned handle
table, session generation, part identity, or invalidation after a part/context
change. `create_box_with_hole` itself changes the active part, yet old handles
remain syntactically usable.

The selection payload also leaves `component_path` and `fingerprint` null in
`NxBridgeEntry.cs:143-151` and `BranchCSmokeRuntime.cs:438-448`. A stale tag can
therefore be applied to the wrong object or fail after a context change,
contrary to HANDOFF 17.3 and the handle-only tool contract.

The `save` tool accepts a handle, but both `Save` handlers ignore it and save
the current work part (`NxBridgeEntry.cs:443-449` and
`BranchCSmokeRuntime.cs:284-288`). A stale or unrelated handle can therefore
still save the wrong part.

### M7. The browser path loses clarification and conversation state

Each browser POST starts a fresh subprocess with one `--message` at
`tools/branch_c_ui_server.py:71-117`. The CLI then creates a new
`AssistantAgent` for that process at `src/drawgen/cli.py:97-100`. The agent
stores conversation state only in that in-memory instance at
`src/drawgen/assistant/agent.py:28-30`.

An ambiguous request can return a clarification, but the user's next browser
message is classified without the prior request or question. This fails the
required clarification state behavior for the browser UI and prevents a
multi-turn plan from being completed.

### M8. The agent loop is unbounded

`AssistantAgent.run` uses `while True` at
`src/drawgen/assistant/agent.py:55` with no configured round limit. The test
`tests/unit/assistant/test_assistant.py` intentionally proves that nine tool
rounds are accepted. The HANDOFF turn contract calls for a configured maximum
starting at eight rounds.

A harness can keep returning new calls indefinitely. The browser has an outer
180-second subprocess timeout, but the CLI has no equivalent and the timeout
does not make already-started NX work safe.

### M9. Bridge timeouts do not report “outcome unknown” or stop the NX request

`BridgeBackend` uses the socket timeout and raises a generic connection error
at `src/drawgen/backends/bridge.py:48-61`. The client does not mark a change as
outcome-unknown. `BridgeServer` accepts `request.Options` but never applies a
deadline or cancellation at `nx_bridge/src/BridgeServer.cs:63-72`, and the
journal dispatcher ignores the options entirely at
`BranchCSmokeRuntime.cs:233-253`.

If NX modifies a part and the response is late, the client reports only a
generic failure. A user can retry and apply the operation twice. HANDOFF 17.2
requires an explicit unknown outcome after a timeout and no automatic replay.

## SHOULD_FIX_IMPORTANT

### S1. Planning, API lookup, and pipeline contracts are not connected to execution

`discover_api_candidates` only attaches catalog IDs to an `OperationPlan` at
`src/drawgen/assistant/planning.py:131-170`. `PipelineStep` and
`PipelineResult` are declarations in
`src/drawgen/contracts/operation_plan.py:63-101`, with no composer or executor.
`ToolCall` has no candidate ID, and `ToolRegistry.execute` does not require a
validated candidate.

The candidate validator is a substring test at
`src/drawgen/assistant/api_search.py:175-199`. A missing TSV silently becomes
an empty catalog at `:97-99`, yet the agent can still invoke any registered
tool. When a tool fails, `AssistantAgent` returns immediately at
`agent.py:111-114` instead of searching the next candidate and replanning.

This means API evidence is prompt context rather than evidence used to choose
or build an operation. The current system can support the handful of compiled
adapters that happen to exist, but not the stated plan, lookup, typed-pipeline,
and replan goal.

### S2. Change previews do not meet HANDOFF 17.6

The preview is a generic string containing a raw handle/path and serialized
arguments at `src/drawgen/assistant/tools/__init__.py:365-373`. It does not
include the target's NX name, old and new values, or a pre-confirmation
highlight. The agent never invokes `highlight_entity` as part of confirmation.

The Tk panel shows the preview only in a message box and drops all
`TurnResult.tool_results` details at `src/drawgen/assistant/panel/app.py:73-81`.
The browser shows no preview or tool call at all. This prevents the user from
reviewing the exact target and change before approving it.

### S3. Session and selection responses do not satisfy the live contracts

Both C# dispatchers hard-code `application = "NX"`, `active_sheet = null`, and
`modified = false` in their context responses. See
`NxBridgeEntry.cs:76-95` and `BranchCSmokeRuntime.cs:379-403`. Selection
responses set `component_path` and `fingerprint` to null, as noted above.

`Measure` implements only area and volume at
`NxBridgeEntry.cs:156-189` and `BranchCSmokeRuntime.cs:451-484`, while the
typed contract advertises length, radius, diameter, distance, and angle. The
registry therefore exposes valid-looking requests that the bridge rejects.

### S4. API and bridge paths are tied to one developer's Windows layout

The default API index is `C:\Users\young\.agents\skills\nxopen-api\data\index.tsv`
at `src/drawgen/assistant/api_search.py:15`. The two C# launchers hard-code
`D:\codes\modeling_assistant` at
`nx_bridge/BranchCSmokeJournal.cs:14-20` and
`nx_bridge/BranchCSmokeLauncher.cs:16-22`. The dispatchers write generated
parts under that same root at
`NxBridgeEntry.cs:368-373` and `BranchCSmokeRuntime.cs:309-313`.

The PowerShell defaults repeat the same drive and repository assumptions at
`tools/start_branch_c_ui.ps1:2` and
`tools/check_branch_c_journal.ps1:2-4`. These paths work only on the author's
seat unless every caller overrides them.

### S5. Token creation, endpoint protection, and the two bridge entry points diverge

`NxBridgeEntry.Main` refuses to start unless an external
`DRAWGEN_BRIDGE_TOKEN` is present at `nx_bridge/src/NxBridgeEntry.cs:21-27`,
while the default PowerShell launcher never sets that variable. The smoke
runtime silently generates a token when the variable is absent at
`BranchCSmokeRuntime.cs:56-67`. Thus the two documented load paths have
different authentication behavior.

Both paths write the token-bearing endpoint with ordinary `File.WriteAllText`
and no user-only ACL. The endpoint is therefore protected only by the token
value and inherited directory permissions, despite HANDOFF 17.2 requiring a
file only the current user can read.

The smoke runtime and add-in duplicate the command implementation instead of
sharing one dispatcher. Their command sets, undo behavior, response encoding,
and token startup behavior already differ. Adding one operation requires
coordinated edits in the registry, both dispatchers, the skill/documentation,
and tests, which is a substantial extensibility cost.

### S6. Session logging is incomplete for FR-29

`SessionLog` writes only a timestamp, event name, and payload at
`src/drawgen/assistant/log.py:12-21`. The agent logs user messages, plans,
harness requests, assistant steps, tool results, and checker results, but it
does not record a distinct tool-call event, confirmation decision, final answer,
model name, or prompt hash. See `src/drawgen/assistant/agent.py:38-43`,
`:64-75`, and `:126-129`.

The browser creates a new CLI session for every request, so its records also do
not form one conversation log.

### S7. Required safety and bridge behavior lacks test coverage

The focused offline run produced 23 passing tests. The socket round-trip test
could not bind a loopback socket in this review sandbox, so no live transport
test ran. More importantly, the committed tests do not cover browser
confirmation, tool-argument number provenance, stale handles, bridge command
parity, C# undo marks, listener-thread dispatch, timeout outcome handling,
endpoint permissions, or log completeness. The mock backend creates an undo
mark for every command at `src/drawgen/backends/live_mock.py:69-83`, which masks
the missing marks in both real C# implementations.

## NEEDS_CONFIRMATION

### N1. NX 2506 and .NET 8 seat behavior is unverified here

No NX or PowerShell runtime is available in the review environment. The C#
code reflects over `NewFaceProperties` and `NewMassProperties` by method name
and parameter count at `NxBridgeEntry.cs:242-319`, rather than binding to a
recorded exact signature. The project references `NXBIN\\managed` in
`nx_bridge/NxBridge.csproj:14-27`, while the journal checker references
`NXBIN\\managed_core` at `tools/check_branch_c_journal.ps1:29-31`.

The smoke runtime also loads `System.Windows.Forms.Timer` from the installed
.NET 8 WindowsDesktop shared framework at
`BranchCSmokeRuntime.cs:78-104`. Whether that assembly is available in the NX
host, whether the timer callback is NX's main thread, whether
`UI.LockAccess()` is sufficient, and whether the reflected measurement
overloads return the stated units require a real NX 2506 seat recording.

### N2. Windows process and encoding behavior needs a seat smoke test

`PiAgentHarness` splits configured arguments with `shlex.split(..., posix=False)`
and only wraps `.cmd` or `.bat` commands with `cmd.exe /d /c` at
`src/drawgen/assistant/harness.py:294-329`. The launcher uses `pi.cmd` and
starts `uv` and Edge through `Start-Process` at
`tools/start_branch_c_ui.ps1:16-37`, while the HTTP server invokes `uv` by name
at `tools/branch_c_ui_server.py:74-117`.

Quoting of a path containing spaces, PATH resolution for `uv`, the installed
pi shim's JSON mode, and the NX host's UTF-8 handling were not executable in
this environment. They need a Windows smoke test with the exact pi and NX
2506 installations.

## Flexibility and rule-7 design input

Rule 7 is binding for this review. Model-generated C# or a model-supplied
journal would violate “the assistant acts on NX only through listed tools” and
NFR-13, even if the bridge compiled it in a temporary process. The current
typed-tool direction is the safe foundation, but it needs a real pipeline
layer.

A rule-7-compliant flexible design would have the model return only
`PipelineStep` references to a registry of compiled, versioned adapters. Each
adapter would own an exact NX2506 API signature, argument schema, handle and
unit checks, and recorded evidence linking the step to an API candidate. The
planner could compose many adapters without knowing NXOpen syntax. The bridge
would accept only allowlisted adapter commands, queue every NXOpen call on the
NX main thread, and attach a session generation to every handle. The shared
change controller would preview each step, highlight targets, obtain explicit
panel confirmation, set one real undo mark per change, return that mark, and
never save implicitly. API lookup would select candidate adapter IDs and a
failed adapter would trigger deterministic fallback or replanning.

Runtime-generated C# would require an explicit change to rule 7 before it
could be considered. If that rule is changed, the minimum safety boundary is
still a closed NXOpen reference allowlist, static inspection of generated
source, compilation in an isolated process, no shell/file/network/reflection
capabilities, signed or approved adapter manifests, bounded execution on the
NX main thread, the same preview/confirmation/undo/save policy, and an
“outcome unknown” state on cancellation. Those controls would reduce risk but
would not make the current implementation compliant with the rule as written.

## Overall classification

The branch has multiple MUST_FIX findings before it can be used against a live
NX session. The highest-risk defects are browser auto-confirmation, missing
real undo marks, listener-thread NXOpen calls, unimplemented advertised tools,
unvalidated numeric arguments, stale raw handles, and missing timeout outcome
handling. The plan/API/pipeline gap is the primary blocker to the owner's
flexibility goal even after those safety defects are addressed.
