# drawgen

AI drawing harness: generates a 2D engineering drawing for a target 3D model by
learning the conventions of a similar reference model and its drawing. Siemens NX
creates the native drawing through NXOpen journals run in batch.

`HANDOFF.md` is the specification. `docs/progress.md` tracks the tasks.

## Setup

```
uv python install 3.10 3.12
uv sync
make check
```

## Commands

| Command | What it does |
|---|---|
| `make check` | lint, types, tests, and the Python 3.10 check for `shared/` |
| `make lint` / `make fmt` | ruff check and format check / apply fixes |
| `make types` | mypy strict, plus a second pass at Python 3.10 for `shared/` and `nx_worker/` |
| `make test` | pytest with coverage |
| `make schemas` | regenerate `schemas/` from the pydantic contracts |
| `uv run pytest tests/contract/test_nfr02.py` | one test file |

## Layout

See HANDOFF.md section 6. `src/drawgen` never imports a CAD API; `nx_worker/`
runs inside NX's Python and is never imported by `src/`.
