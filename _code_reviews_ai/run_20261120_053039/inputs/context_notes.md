# Context Notes

Test/gate evidence:
- `make gate` currently fails on 3 pre-existing ruff errors in tools/branch_c_ui_server.py (import order, two unused `# noqa: N802`). Not caused by this review.
- docs/progress.md reports 289 passing Python tests offline; this was not re-run for this review.

Known unknowns (do not invent):
- NX is not installed on the review machine (macOS). No C# build, no NX run, no PowerShell execution is possible here; runtime claims about NX behaviour must be marked needs_confirmation.
- The NXOpen API index referenced by api_search.py (a TSV on the Windows seat) is not in the repository.
- Assumptions A9-A13 (HANDOFF 4.5) are unconfirmed by the owner.
- The exact pi CLI version and flags on the seat are unknown.
