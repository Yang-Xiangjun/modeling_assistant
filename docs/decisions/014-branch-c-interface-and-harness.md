# 014 Branch C bridge and harness portability

Status: partially decided 2026-11-16.

## Bridge

- The live NX interface is a compiled C# NXOpen add-in loaded into the user's interactive NX session.
- `nx_bridge/` is the only layer allowed to call NXOpen.
- The add-in owns the NX object handle table, main-thread dispatch, loopback listener, token validation, and bridge status responses.
- Python code owns contracts, tool policy, confirmation, number checking, logging, and test doubles.
- The exact NX release, .NET target framework, build toolchain, add-in load mechanism, and main-thread callback API remain seat-level confirmations before C0-T2.

## Harness portability

- Assistant and drawing code depend on a provider-neutral `HarnessAdapter`/`LlmClient` port, never on Codex CLI, Claude Code, Pi, or another concrete harness.
- Every adapter accepts a versioned JSON request containing the conversation, tool specifications, context summary, and prior tool results, and returns only a validated `AssistantStep`.
- Adapters run as local subprocesses or local HTTP clients behind one timeout, cancellation, logging, and error wrapper. They may not access NXOpen or execute model-produced code.
- `FakeHarness` and record/replay traces are the CI reference. A first real CLI adapter is required for the MVP; additional adapters must fit the same contract without changes to `assistant/`, `tools/`, or the bridge.
- The first real adapters are the OpenAI Responses/Codex API and pi's JSON-mode CLI. Codex uses `OPENAI_API_KEY` or `CODEX_API_KEY`; pi is configured with `DRAWGEN_PI_COMMAND` and `DRAWGEN_PI_ARGS`.
- The default harness, supported CLI versions, command lines, structured-output mode, authentication, streaming behavior, and privacy boundary remain confirmations before C1-T4.

## Consequence

C0 may implement contracts, `MockLiveBackend`, and fake bridge tests before those seat decisions. It must not implement the C# add-in or hosted harness adapter until the confirmations above are recorded.
