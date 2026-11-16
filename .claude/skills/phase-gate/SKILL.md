---
name: phase-gate
description: Close a phase at its gate. Runs all checks, updates docs/progress.md, and writes the gate report with the checklist of HUMAN and EXPERT tasks.
disable-model-invocation: true
---

# Phase gate

Run this when the `[CC]` tasks of a phase are done. Argument: the phase, for
example `P1`. Without one, take the current phase from `docs/progress.md`.

1. **Run every check** and keep the summary lines:
   - `make check`
   - `uv run python tools/export_schemas.py --check`
   - `uv run python tools/make_synthetic.py --check`
   - `uv run drawgen ping --backend nx` to learn whether NX is reachable here
   If anything fails, fix it or report it. Do not write a passing report.
2. **Compare with HANDOFF.md section 14** for the phase: every `[CC]` task has a
   commit with its ID, and its "done when" condition holds. List gaps honestly.
3. **Check the rules** in HANDOFF.md section 2 and the definition of done in
   section 15. Grep `nx_worker/` for `UNVERIFIED-NXOPEN` and confirm each one is
   in `docs/nx_api_assumptions.md`.
4. **Update `docs/progress.md`:** task status, and a section for the next phase.
5. **Write `docs/gates/G<n>-report.md`** with:
   - the summary lines from step 1;
   - what passed, by task ID, and which requirement or acceptance criterion it serves;
   - what could not be done or was done differently from HANDOFF.md, and why;
   - open questions from section 16 that block the next phase;
   - a checklist of every `[HUMAN]` and `[EXPERT]` task for this gate. Each item
     states what to do, the exact command or the journal to record, which files
     to put where, and what to send back.
6. **Commit** as `<phase>-gate: report`. Summarise the report to the owner and
   stop. Do not start the next phase until they say so.
