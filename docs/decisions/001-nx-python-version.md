# 001 NX Python version (open question 1)

Status: default taken 2026-11-16, to be confirmed by P0-H1.

`shared/` and `nx_worker/` target Python 3.10 with the standard library only, as HANDOFF.md section 7 reports for NX 2406. `make check` runs them on a real 3.10 interpreter. If the seat reports another version, change the ruff target, `mypy-py310.ini` and the `py310` make target.
