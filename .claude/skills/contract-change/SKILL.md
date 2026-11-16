---
name: contract-change
description: Procedure for changing a data contract. Use when adding, removing, renaming or retyping a field in src/drawgen/contracts, or when schemas/ must change.
---

# Changing a data contract

Contracts are the only thing the layers share, and the worker conforms to the
exported schemas without importing them. Do every step, in order.

1. **Check the rules first.** Read HANDOFF.md section 8 for the contract. If the
   change adds a number or an untyped field to `DrawingPlan` or `PlanSelection`,
   stop: that breaks NFR-02 and needs the owner's decision.
2. **Update the pydantic model** in `src/drawgen/contracts/`. Models hold no
   logic. Keep `extra="forbid"`. A new top-level contract also goes into
   `registry.py`.
3. **Regenerate the schemas:** `make schemas`. Commit the changed files in `schemas/`.
4. **Update the sample** in `tests/contract/samples.py` so the round-trip test
   still spells out every field.
5. **Update the synthetic generator** `tools/make_synthetic.py` if the contract
   is one it writes, then `make synthetic` and commit the regenerated fixtures.
6. **Update golden expectations** under `tests/golden/` when pipeline output
   changes, and say why in the commit message.
7. **Update the worker side** if the contract crosses the process boundary:
   the plain-dict code in `nx_worker/` and the validation in
   `src/drawgen/backends/nx.py`. Real fixtures under `fixtures/real/` cannot be
   regenerated here; list them in the decision note as needing a re-run on the seat.
8. **Re-run the NFR-02 test:** `uv run pytest tests/contract/test_nfr02.py -q`.
   Its allow-list may change only together with a decision note.
9. **Add a decision note** `docs/decisions/NNN-title.md`: what changed, why, and
   which fixtures or recordings are affected. Before P5-T4 the schema string
   stays at `/0`; after the freeze, a breaking change bumps it.
10. **Run `make check`** and commit with the task ID prefix.
