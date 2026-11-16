---
paths:
  - "nx_worker/**"
  - "shared/**"
---

# Rules for nx_worker/ and shared/

This code runs inside the Python bundled with NX.

- **Python 3.10 syntax only.** No `type` statements, no PEP 695 generics, no
  `except*`, no `tomllib`, no `typing.Self`, no `enum.StrEnum`.
- **Standard library only.** No pydantic, no numpy, nothing from PyPI. The only
  first-party imports are `drawgen_shared` and `nx_worker`. Never import `drawgen`.
  The worker reads and writes plain dicts that conform to `schemas/`.
- **`import NXOpen`** appears only under `nx_worker/commands/` and
  `nx_worker/nxutil/`, never in `nx_worker/main.py` and never in `shared/`.
- **Do not invent NXOpen API calls.** Every NXOpen call must be one of:
  1. copied from a journal in `nx_worker/recorded/`, recorded by a person in the
     real NX release;
  2. listed in HANDOFF.md section 13;
  3. marked with the comment `# UNVERIFIED-NXOPEN` and added to
     `docs/nx_api_assumptions.md` with the recording that would verify it.
  When a needed call is not available, write the recording request into
  `docs/nx_api_assumptions.md` and continue with other work.
- **Worker behaviour** (HANDOFF.md section 9): no user-interface calls; open parts
  by file path; never save a source part; always write `status.json`, also on
  failure; never attach a dimension to a guessed entity.
- Follow the `nx-journal` skill when adding or changing a worker command.
- Check with `make py310` and `make arch` in addition to `make check`.
