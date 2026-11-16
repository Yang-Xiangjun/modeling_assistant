# Progress

Specification: `HANDOFF.md`. Branch: `p0-setup`. Update this file with every task.

## P0 Setup (gate G0: a journal runs in batch on the reference files)

| Task | Owner | Status | Notes |
|---|---|---|---|
| P0-T1 scaffold, tooling, `make check`, CI workflow | CC | done | CI workflow targets GitHub Actions (decision 007); no remote yet |
| P0-T2 contracts as pydantic models, schema export, NFR-02 test | CC | done | refinements in decision 009; NFR-02 enforced by `tests/contract/test_nfr02.py` |
| P0-T3 `drawgen_shared` | CC | done | implemented by Codex, reviewed; edge centroid and arc box choices in decision 010 |
| P0-T4 synthetic generator and fixtures | CC | done | implemented by Codex; side-view rotation fixed in review; see decision 011 |
| P0-T5 worker skeleton, `ping`, backends, `drawgen ping` | CC | todo | |
| P0-T6 architecture tests | CC | todo | |
| P0-H1 NX release, Python version, parts on the seat, recorded journals | HUMAN | todo | |
| P0-H2 run `ping` through `run_journal`, commit `status.json` | HUMAN | todo | gate G0 |

Also pending for this branch: Claude Code setup (CLAUDE.md, rules, skills, Stop hook).

## Open questions (HANDOFF.md section 16)

None blocks P0. Defaults taken are in `docs/decisions/001` to `007`.
