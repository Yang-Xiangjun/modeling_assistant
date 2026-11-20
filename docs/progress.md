# Progress

Specification: `HANDOFF.md`. Branch: `p0-setup`. Update this file with every task.

## P0 Setup (gate G0: a journal runs in batch on the reference files)

| Task | Owner | Status | Notes |
|---|---|---|---|
| P0-T1 scaffold, tooling, `make check`, CI workflow | CC | done | CI workflow targets GitHub Actions (decision 007); no remote yet |
| P0-T2 contracts as pydantic models, schema export, NFR-02 test | CC | done | refinements in decision 009; NFR-02 enforced by `tests/contract/test_nfr02.py` |
| P0-T3 `drawgen_shared` | CC | done | implemented by Codex, reviewed; edge centroid and arc box choices in decision 010 |
| P0-T4 synthetic generator and fixtures | CC | done | implemented by Codex; side-view rotation fixed in review; see decision 011 |
| P0-T5 worker skeleton, `ping`, backends, `drawgen ping` | CC | done | implemented by Codex, reviewed; see decision 012 |
| P0-T6 architecture tests | CC | done | implemented by Codex; pack-name scan scope fixed in review; `make gate` runs lint, types and these tests |
| P0-H1 NX release, Python version, parts on the seat, recorded journals | HUMAN | todo | |
| P0-H2 run `ping` through `run_journal`, commit `status.json` | HUMAN | todo | gate G0 |

Claude Code setup is done: `CLAUDE.md`, `.claude/rules/nx-worker.md`, the skills
`nx-journal`, `contract-change` and `phase-gate`, and a Stop hook that runs `make gate`.

All `[CC]` tasks of P0 are done. Gate G0 waits for P0-H1 and P0-H2. The exact
steps for the person on the NX seat are in `nx_worker/README.md` and
`docs/nx_api_assumptions.md`.

## Open questions (HANDOFF.md section 16)

None blocks P0. Defaults taken are in `docs/decisions/001` to `007`.

## Branch C assistant track

Implementation plan: [docs/branch-c-implementation-plan.md](branch-c-implementation-plan.md). No C0 implementation is marked done; C0-H1/C0-H2 and assumptions A9-A13 remain the entry gate.

Owner update: C# NXOpen is the selected bridge direction. Before C0-T2, confirm the NX release/.NET target/build and add-in load path, NX main-thread dispatch API, panel placement, transport/token policy, and the fixed operation list. Before C1-T4, confirm the first supported harness CLI and the provider-neutral adapter contract described in decision 014.

Implementation started: live contracts, MockLiveBackend, BridgeBackend, Codex Responses adapter, pi JSON-mode adapter, CLI chat/panel, typed tools, confirmation/undo policy, and a buildable NX2506 C# bridge scaffold are present. The MVP planning slice now classifies requests, asks for clarification before complex execution, attaches local NXOpen API candidates through synonym search, and passes the plan and evidence into every harness turn. Area and volume measurement, including the NX2506 C# volume adapter, are covered by the offline tests. Real NX selection/operation dispatch remains a seat recording task.

Current offline validation is 289 Python tests, Ruff, strict mypy, and exported-schema checks. The C# bridge builds with `NX_ROOT=D:\softwares\NX2506`. The remaining human gate is to load the journal in interactive NX and verify live selection, measurement, and box-with-hole behavior.

Manual startup is consolidated in `tools/start_branch_c_manual_test.ps1`. It builds the bridge, starts NX and the browser assistant, and enables the deterministic smoke fixture before the journal is loaded.

The interactive journal is now a reference-only loader. `tools/build_branch_c.ps1` also runs `tools/check_branch_c_journal.ps1`, which catches NX journal compiler reference errors before a manual test starts.
