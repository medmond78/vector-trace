@AGENTS.md

# vector-trace: project status

PRD: `PRD.md` (design/roadmap, milestones M1-M4, v2/v3+). This section tracks
what's actually built, since implementation has diverged from and extended
past the PRD in places.

## Implemented

- `extract IMAGE --xcal .. --ycal ..`: M1 core pipeline (Sobel plot-area
  detection, calibration, trace one curve, CSV + overlay PNG). Plus
  `--seed X,Y` (FR8 color seed) and `--color NAME|HEX` (not in PRD) to pick a
  curve by its color instead of a pixel.
- `colors IMAGE`: lists the plot's dominant stroke colors (hex, nearest
  CSS3/X11 name, color-square emoji). No curve extraction. Not in the PRD.
- `preview IMAGE [OPACITY]`: shows the traced curve in a GUI window
  (`cv2.imshow`), overlaid on a faded copy of the image; writes nothing to
  disk. Takes `--seed`/`--color` like `extract`. Needs a GUI-capable OpenCV
  build (`opencv-python`, not `opencv-python-headless`). **Name collision
  with the PRD's `preview` command**, which is a different, unimplemented
  feature (numbered-tick calibration image from a PDF page) — see below.
- Log axes (`--xlog`/`--ylog`), `--frame` override, `--man` full manual
  (FR3-FR5).

## Not implemented (PRD scope)

- PDF input (`--page`/`--crop`, FR1/FR2). v1 is raster-image-only; PDFs must
  be exported to an image first.
- The PRD's `preview` (numbered-tick calibration image) and `candidates`
  (labelled centerline candidates) commands.
- `--mask` exclude regions (FR12), JSON sidecar (FR14b), tilt correction
  (FR6), error estimate (FR15).
- Dashed/dotted curve gap bridging (FR11) —
  `tests/test_extract.py::test_dashed_covers_x_range` is an expected failure
  (`xfail`, M3).
- Scatter/marker plots and batch processing remain out of scope (PRD v2/v3+).

## Code map

- `vector_trace/core.py` — curve tracing (Sobel edges, or seed/direct-color
  stroke masking), plot-frame detection, calibration math.
- `vector_trace/colors.py` — dominant-color k-means clustering, CSS3/X11 name
  table, color-square emoji matching, hex/name parsing for `--color`.
- `vector_trace/cli.py` — argparse CLI for `extract`/`colors`/`preview`.
- `vector_trace/man.py` — the `--man` manual text (kept in sync with
  `--help`; `tests/test_cli.py::test_man_documents_every_option` checks every
  `extract --help` flag appears in `--man`).
- `tests/` — synthetic-plot tests (`synthetic.py` generates matplotlib
  figures with known ground truth) plus CLI integration tests per command.
