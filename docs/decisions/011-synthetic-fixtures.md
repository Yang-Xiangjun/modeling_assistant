# 011 Synthetic PCBA fixtures

Status: decided 2026-11-16 (P0-T4).

- `tools/make_synthetic.py` writes `fixtures/synthetic/pcba/`: `reference` gets a
  model and a drawing; `sibling_board_size`, `sibling_moved_holes` and
  `sibling_extra_connector` get a model only, like the real golden set.
- Every body is a complete box or pin with all faces and edges, so recognition
  in P1 sees closed geometry. Holes and vias are concave cylinders through the
  board. Pins are convex cylinders in their own bodies inside the connector
  component.
- The datum for mounting-hole ordinates is the first mounting hole. Connector
  location is measured from that datum to pin 1.
- The drawing uses ISO, first-angle, A3, no template (see decision 003). The side
  view is the NX "Front" orientation: it looks along +Y and keeps +Z up.
- `--check` and a test fail when committed fixtures differ from regeneration.
- The generator lives in `tools/` and its tests in `tests/tools/`. Both name the
  PCBA product, so the P0-T6 pack-name test exempts `tools/`, `fixtures/` and
  `tests/tools/`. Rule 6 covers core, harness and worker, which stay clean.
