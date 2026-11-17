# drawgen

Two parts. Drawing generation plans a 2D drawing for a target 3D model from a
reference model and drawing; deterministic code measures and verifies, and NX
draws through NXOpen journals run in batch (phases P0 to P5). A chat assistant
docked beside NX reads the live session and runs a fixed list of tools through
a bridge add-in inside NX (phases C0 to C3).

The specification is `HANDOFF.md` at the repository root. It is long: read only
the sections listed below for the work at hand. Task status is in
`docs/progress.md`. Settled decisions are in `docs/decisions/`.

## Commands

| Purpose | Command |
|---|---|
| Everything (run before every commit) | `make check` |
| One test file | `uv run pytest tests/contract/test_nfr02.py -q` |
| One test | `uv run pytest tests/unit/shared/test_vec.py -k normalize -q` |
| Lint / apply fixes | `make lint` / `make fmt` |
| Types (3.12 everywhere, 3.10 for shared/ and nx_worker/) | `make types` |
| Architecture tests | `make arch` |
| Fast gate: lint, types, architecture | `make gate` |
| shared/ and worker on a bare Python 3.10 | `make py310` |
| Regenerate `schemas/` | `make schemas` |
| Regenerate synthetic fixtures | `make synthetic` |
| Ping a backend | `uv run drawgen ping [--backend nx]` |

Use `uv run` for every Python command. The system `python3` is 3.9 and wrong.

## Rules that override everything

If a task conflicts with one of these, stop and ask.

1. Every measurement comes from the CAD model, never from an LLM or a reference drawing.
2. Tolerances, datums and GD&T are never copied from a reference without an
   authoritative source. Without one, flag them for human review.
3. The LLM only selects among IDs that deterministic code produced.
4. `src/` never imports a CAD API. Backends run as separate processes.
5. A failed check leaves the drawing unreleased and reported, never silently saved.
6. Core, harness and worker never name a product type. Product knowledge lives in packs.
7. The assistant acts on NX only through listed tools. It never runs NXOpen code
   written by a model.
8. A tool that changes a part runs only after the user confirms, sets an undo
   mark first, and never saves on its own.

## Working limits

- NX is not installed here. Check with `uv run drawgen ping --backend nx`. Tasks
  tagged `[HUMAN]` or `[EXPERT]` are prepared, not done: write the instructions and stop.
- Never invent an NXOpen call, in the worker or the bridge. Use the `nx-journal`
  skill for any worker change.
- Assumptions A9 to A13 (HANDOFF.md 4.5) are unconfirmed. Do not start a task
  that depends on one. No bridge or panel toolchain before the C0 decisions.
- Never create a file under `fixtures/real/`. Synthetic data carries `"synthetic": true`.
- Real fixtures may be confidential: never paste their content into tests, logs or docs.
- No CAD libraries in this repository (no pythonOCC, FreeCAD, CadQuery).
- `shared/` and `nx_worker/`: Python 3.10 syntax, standard library only.
- Do not let a formatter touch `HANDOFF.md`. ruff excludes Markdown for this reason.
- Work one phase at a time. At a gate, run the `phase-gate` skill and wait.
- Commits: one task per commit, message prefixed with the task ID, e.g. `P1-T3: ...`.
- Record every decision HANDOFF.md leaves open in `docs/decisions/NNN-title.md`.

## Read before working on

| Work | HANDOFF.md section |
|---|---|
| Any task: its entry, and the definition of done | 14, 15 |
| Layers and which package may import what | 5, then `tests/arch/` |
| Where a file belongs | 6 |
| Tooling, units, determinism, test expectations | 7 |
| A data contract (`src/drawgen/contracts/`, `schemas/`) | 8, and use the `contract-change` skill |
| Fingerprints and tolerant matching (`shared/`) | 8.1 |
| The worker (`nx_worker/`), `job.json`, `status.json`, backends | 9, 3, 13 |
| A product pack, the PCBA heuristics and rules | 10 |
| Verification rules S-01 to S-06 and V-01 to V-07 | 11 |
| The harness, LLM client, repair loop, review gate (P4) | 12 |
| Requirements and acceptance criteria by ID (FR, NFR, AC) | 4 |
| The chat assistant, tools, live backends, the bridge (`nx_bridge/`) | 17, 13, 4.5 |
| Questions still open: ask, do not assume | 16 |

## Where things are

- `src/drawgen/contracts/` pydantic models, no logic. `registry.py` lists them all.
- `shared/drawgen_shared/` vectors, frames, canonical JSON, fingerprints.
- `src/drawgen/backends/` `CadBackend`, `MockBackend`, `NxBackend`.
- `nx_worker/` runs inside NX. `recorded/` holds journals recorded by a person.
- `tools/` schema export and the synthetic generator. `fixtures/synthetic/` its output.
- `tests/` `unit/`, `contract/` (round-trip, NFR-02), `arch/`, `tools/`, `golden/`.
- `docs/nx_api_assumptions.md` every NXOpen call or runtime behaviour not yet verified.
- Not created yet: `src/drawgen/assistant/`, `backends/live.py`, `nx_bridge/` (C0 on).

## Delegating to Codex

The owner wants clear, well-specified tasks handed to Codex with `/codex:rescue`,
then reviewed here. Give it a full written spec and the constraints above. Its
sandbox cannot use `uv run`, so tell it to use `.venv/bin` tools once and stop.
Always run `make check` yourself and review the diff before committing.
