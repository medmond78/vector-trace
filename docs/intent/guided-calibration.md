# Intent: guided calibration mode

Confirmed via `/interview-me`, 2026-10-19.

- **Outcome:** A new guided mode that lets you click calibration points (2
  x-axis, 2 y-axis — linear or log) and pick the curve by click or color,
  then runs the extraction immediately and writes `curve.csv` + overlay —
  plus prints the equivalent `extract --xcal ... --ycal ...` command
  alongside, so you still get a reproducible, tweakable record.
- **User:** the project owner, solo, digitizing real journal-figure images.
- **Why now:** extraction accuracy is already trusted; the pixel-hunting
  round-trip (read a pixel in `preview`, hand-type it into `extract`) is the
  biggest remaining friction.
- **Success:** go from image to `curve.csv` without manually retyping a
  single pixel coordinate, for the common linear- or log-axis case.
- **Constraint:** fully additive — the existing `extract`/`colors`/`preview`
  flag-based commands stay exactly as they are, untouched.
- **Out of scope:** `--frame` override, `--tol`/`--thr` tuning,
  multi-curve-per-run, and PDF input all stay CLI-only/unchanged — the
  guided mode only covers calibration + curve-pick for the common case.

## Interaction model (confirmed)

- Click-then-type, alternating: click a point in the preview window, type
  its value in the terminal, repeat. The user asked for "detailed
  instructions" at each step — the guided mode must clearly prompt which
  point it's waiting for.

## Not yet decided (implementation planning)

- Command name/invocation shape (new subcommand vs. a flag).
- Exact step order (calibration points vs. curve pick first).
- Whether curve selection offers both click-to-seed and type-a-color, same
  as `extract`'s `--seed`/`--color`.
