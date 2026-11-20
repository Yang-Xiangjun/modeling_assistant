# Consensus, cycle 01

Reviewers: reviewer_01, reviewer_02, reviewer_03 (independent first pass, codex-cli 0.169.0).
Orchestrator re-verified every blocking finding against the code at `d3923a8`
(unchanged by the lint-only commit `9c6406b`). Mode: basic review and plan; no
fix loop this session, so `fix_log.md` lists the items as `open`.

Votes: R1 / R2 / R3. M = MUST_FIX, S = SHOULD_FIX_IMPORTANT, m = minor, N = needs confirmation, - = not raised.

## must_fix (blocking)

| ID | Finding | Votes | Re-verified at |
|---|---|---|---|
| C1 | Browser path auto-confirms every change (`--yes`, `DRAWGEN_UI_AUTO_CONFIRM` defaults on) | M/M/M | `tools/branch_c_ui_server.py:67,98-99`, `tools/start_branch_c_ui.ps1:19` |
| C2 | Change commands return fake or null undo marks; only `update` calls `SetUndoMark` | M/M/M | `BranchCSmokeRuntime.cs:280,623-647`, `NxBridgeEntry.cs:322-344,352-440` |
| C3 | Compiled add-in calls NXOpen from the async listener task (no main-thread queue) | M/M/M | `BridgeServer.cs:51-72`, `NxBridgeEntry.cs:49-74` |
| C4 | LLM-visible tools that neither dispatcher implements; no capability handshake | M/M/M | `tools/__init__.py:262-349` vs `NxBridgeEntry.cs:54-67`, `BranchCSmokeRuntime.cs:264-290` |
| C5 | Handles are raw global tags, never invalidated; `save` ignores its handle | M/M/M | `NxBridgeEntry.cs:443-470`, `BranchCSmokeRuntime.cs:284-288,650-669` |
| C6 | Numbers in tool arguments are never provenance-checked; answer checker has no display-precision rounding or count rule | M/S/M | `agent.py:51-78`, `tools/__init__.py:354-379`, `checker.py:30-38` |
| C7 | Timed-out change gives a generic error, not "outcome unknown"; bridge ignores `options.timeout_s` | M/S/M | `bridge.py:48-61`, `BridgeServer.cs:63-72` |
| C8 | Clarification and conversation state is lost (browser starts a new process per message; agent stores no pending plan) | M/S/M | `branch_c_ui_server.py:72-117`, `agent.py:41-50` |

## should_fix_important (blocking)

| ID | Finding | Votes |
|---|---|---|
| S1 | Plan, API lookup and `PipelineStep`/`PipelineResult` are not connected to execution; no replanning on failure | S/S/M |
| S2 | Change preview lacks target name, old/new values and highlight; browser shows no tool calls or results | S/m/S |
| S3 | Context and selection contract gaps: `modified` always false, `fingerprint`/`component_path` null, only area and volume measured | S/S/S |
| S4 | Windows portability: `D:\codes\modeling_assistant` and a user-profile path hard-coded; `dotnet build --no-restore`; `NXBIN\managed` vs `managed_core` | S/S/S |
| S5 | Endpoint and token: no user-only ACL, client trusts `host` from the file, token provisioning differs between the two load paths, multiple clients accepted | S/N/S |
| S6 | Smoke runtime parses JSON with regexes (order-sensitive `measure`) and drains the whole queue in one UI tick | -/S/S |
| S7 | Two diverging C# dispatchers; one operation needs edits in about 7 places | S/S/S |
| S8 | Session log lacks tool-call, confirmation, model and prompt-hash events; browser makes one log per message | S/-/S |
| S9 | Tests exercise only the mock, which invents undo marks; no fault, stale-handle, provenance or C# tests | S/S/S |
| S10 | Default launch creates and saves a fixture part before any chat confirmation | M/S/- |
| S11 | Synthesis: UI server accepts cross-origin `POST /api/chat` with any content type; with C1 a web page could drive NX | -/-/- (orchestrator, verified `branch_c_ui_server.py:164-178`) |
| S12 | Synthesis: planner misclassifies clear requests as ambiguous ("hide this body", "save the part", any non-English text) | -/-/- (orchestrator, reproduced) |

## needs_confirmation (owner decision or NX seat)

| ID | Item |
|---|---|
| N1 | Round cap: HANDOFF 17.5 says a configured cap starting at 8; the Branch C plan removed it on purpose. R1 and R3 flag it as a defect. Owner must pick one and record a decision. |
| N2 | NX 2506 behaviour: reflected `NewFaceProperties`/`NewMassProperties`, whether the WinForms timer runs on NX's main thread, `UI.LockAccess` semantics. |
| N3 | pi CLI version, `--print --mode json` event shape, `pi.cmd` quoting through `cmd.exe /d /c`. |
| N4 | Rule 7 vs the owner's flexibility goal (pi forms an NXOpen C# pipeline). All three reviewers: model-written C# executed in NX violates rule 7 as written; a model-composed pipeline of compiled typed adapters is compliant. |

## rejected_with_reason

None. R3's "Create a box gets default dimensions" is merged into C6 and S12. The R2 preview item is raised to S2 by majority.
