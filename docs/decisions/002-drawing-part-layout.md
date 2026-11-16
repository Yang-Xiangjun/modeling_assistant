# 002 Drawing part layout (open question 2)

Status: default taken 2026-11-16.

Not known whether each drawing is a separate part that references its model. `RawDrawing.source.model_part` is nullable and reports it. Synthetic fixtures use the separate-part form. `extract_drawing` (P1) must handle both.
