# 010 Fingerprint details left open by HANDOFF.md section 8.1

Status: decided 2026-11-16 (P0-T3).

- **Edge centroid.** A circle or arc edge uses its centre. A line uses the
  midpoint of its start and end. Without either, computing the fingerprint fails.
- **Circle and arc boxes.** Both use the box of the full circle. For an arc this
  is larger than the true extent, but the box is not a match criterion, so it
  only affects reporting.
- **Missing values.** A direction or radius matches only if both sides have one,
  or both have none.
- **Size.** Equal when within either the relative or the absolute tolerance.
- **Tolerances.** `drawgen_shared.tolerances` mirrors the contract defaults.
  `tests/contract/test_tolerances_agree.py` checks that they agree.
