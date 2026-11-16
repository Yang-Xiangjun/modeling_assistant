# 008 Python version and tooling

Status: decided 2026-11-16.

- `src/` runs on Python 3.12 (`.python-version`); `requires-python` stays `>=3.11` as specified.
- Tools as HANDOFF.md section 7: uv, ruff, mypy strict, pytest. `make check` is the single entry point.
- mypy runs twice: once at 3.12 over everything, once at 3.10 over `shared/` and `nx_worker/` (`mypy-py310.ini`), because mypy has no per-directory Python version.
- ruff gets the py310 target through `ruff.toml` files in `shared/` and `nx_worker/`.
- One distribution, `drawgen`, ships both `src/drawgen` and `shared/drawgen_shared`.
- The CLI uses argparse to avoid a dependency.
- No coverage threshold is enforced yet; `core/` is empty in P0.
