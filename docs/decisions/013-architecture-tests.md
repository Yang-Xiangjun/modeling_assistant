# 013 Architecture tests

Status: decided 2026-11-16 (P0-T6).

- Tests in `tests/arch/` parse the source with `ast`. They never import it.
- **Import table.** HANDOFF.md section 5, plus two additions: `drawgen.cli` is the
  composition root and may import any `drawgen` package except a concrete pack;
  packs may import `yaml` for their `config.yaml`; the harness may import
  `langgraph` and `pydantic`.
- **Pack names.** The scan covers `src/drawgen` outside `packs/`, `shared/`,
  `nx_worker/` and the tests outside `tests/tools`, `tests/packs`, `tests/golden`
  and `tests/arch`. `tools/`, `fixtures/`, `docs/` and `schemas/` are exempt
  (decision 011). A line may opt out with the marker `arch: allow-pack-name`;
  one test uses it for a fixture path.
- **Python 3.10.** Every file in `shared/` and `nx_worker/` must parse with the
  3.10 grammar, in addition to the real 3.10 test run in `make py310`.
- `make gate` runs lint, both type checks and `tests/arch`. The Stop hook uses it.
