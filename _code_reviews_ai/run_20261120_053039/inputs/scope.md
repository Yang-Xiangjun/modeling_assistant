# Scope

What was implemented: the Branch C MVP chat assistant and NX bridge (single commit d3923a8).

- Python assistant: src/drawgen/assistant/ (agent, planning, api_search, harness, tools, checker, log, contracts, panel)
- Live backends: src/drawgen/backends/live.py, live_mock.py, bridge.py
- Contracts: src/drawgen/contracts/live.py, operation_plan.py
- CLI wiring: src/drawgen/cli.py
- C# bridge: nx_bridge/src/BranchCSmokeRuntime.cs (the runtime the journal actually loads), nx_bridge/src/NxBridgeEntry.cs (add-in form), BridgeServer.cs, BridgeProtocol.cs, nx_bridge/BranchCSmokeJournal.cs
- Browser UI path: tools/branch_c_ui_server.py, web/branch_c_chat.html, tools/*.ps1
- pi skill: .pi-agent/skills/nxopen-cad/SKILL.md
- Tests: tests/unit/assistant/, tests/unit/backends/test_live*.py

Out of scope: drawing-generation track (P0-P5), shared/, nx_worker/, tools/make_synthetic.py, schemas/ (generated).
