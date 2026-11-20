# drawgen

AI drawing harness: generates a 2D engineering drawing for a target 3D model by
learning the conventions of a similar reference model and its drawing. Siemens NX
creates the native drawing through NXOpen journals run in batch.

`HANDOFF.md` is the specification. `docs/progress.md` tracks the tasks.
The current component map and runtime data flows are documented in
[`docs/architecture.md`](docs/architecture.md).

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

## Branch C MVP

The first assistant slice is available without NX through the scripted live
backend:

```text
uv run drawgen live ping --backend mock
uv run drawgen live selection --backend mock
uv run drawgen assistant chat --backend mock --harness fake --message "what is the area of this face?"
uv run drawgen assistant panel --backend mock --harness fake
```

The assistant CLI defaults to the Pi JSON harness. Install the `pi` CLI and
override `DRAWGEN_PI_COMMAND` and `DRAWGEN_PI_ARGS` when the installed pi
distribution uses different flags. For Codex Responses API chat, set
`OPENAI_API_KEY` and optionally `DRAWGEN_CODEX_MODEL`, then use
`--harness codex`.

The C# bridge project is under `nx_bridge/` and builds against NX2506 with
`NX_ROOT=D:\softwares\NX2506`. Its first interactive dispatcher handles
session context, current selection, selected-face/body area and volume, and reversible display
operations. The assistant performs plan-first clarification and local NXOpen API
candidate discovery before handing a typed request to Pi. `nx_bridge\BranchCSmokeJournal.cs` is the seat smoke fixture and
can be loaded with NX's interactive Journal > Play command.

For a new manual test, run `tools\start_branch_c_manual_test.ps1`. It builds
the bridge, starts NX and the browser, and prepares the deterministic smoke
part. The only NX-side action is loading the journal path printed by the
PowerShell window through **Tools > Journal > Play**.

## Layout

See HANDOFF.md section 6. `src/drawgen` never imports a CAD API; `nx_worker/`
runs inside NX's Python and is never imported by `src/`.
