# Audit Items

1. Rule 8 / HANDOFF 17.6: every change tool shows a preview, waits for an explicit user confirmation in the panel, sets a real undo mark before modifying, returns that mark, and never saves implicitly. Check both Python (tool layer, CLI, UI server, launch scripts) and C# (both dispatchers).
2. HANDOFF 17.2: every NXOpen call runs on NX's main thread; listener threads only queue. Loopback only, per-session token, request ID echo, no replay after timeout.
3. Rule 7 / NFR-13: no tool accepts code, journals, executable paths or shell commands; nothing executes model-written NXOpen.
4. Tool list vs bridge: every tool offered to the LLM is actually implemented by the bridge that is loaded.
5. Planning and clarification (planning.py): requests are classified correctly; clarification state survives across turns, including in the browser UI path.
6. API lookup (api_search.py): is the evidence actually used to choose or build an operation? Is the pipeline contract (PipelineStep/PipelineResult) implemented?
7. Number checker (HANDOFF 17.5): matching rule, rounding at displayed precision, counts, tool-argument numbers.
8. Session handles: session-local, invalidated after part/context changes, never resolved from descriptions.
9. Windows runtime: hard-coded absolute paths, assembly loading, process launching (cmd.exe /c for .cmd shims), UTF-8 handling, PowerShell script robustness.
10. Extensibility cost: how many places must change to add one new NX operation; duplication between BranchCSmokeRuntime.cs and NxBridgeEntry.cs.
11. Test coverage for the above (fault injection, no-confirmation-no-change, bridge failures).
