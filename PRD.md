# PRD: vector-trace, Sobel-based 2D plot digitizer

Status: Draft v0.3 | Owner: TBD | Date: 2026-10-15

## 1. Summary

vector-trace is a command-line tool that converts an image of a 2D plot (a figure from a journal PDF or a PNG) into numeric (x, y) data. It uses Sobel gradient edge detection to find axes, ticks and data curves, then maps pixel coordinates to data coordinates through a user-supplied axis calibration. Output is CSV/JSON that can be used directly in analysis.

## 2. Problem

Published data often exist only as plot images. Re-keying values by hand is slow, subjective and not reproducible. Manual click-to-digitize tools need one click per point, and results differ between operators. We need a repeatable, semi-automatic method where the algorithm proposes the curve and the user only supplies the calibration and picks which curve to keep.

## 3. Goals

- G1: Extract a continuous line/curve from a plot image with minimal input (calibration values plus a curve choice).
- G2: Detect axes and plot area automatically, with CLI overrides.
- G3: Support linear and log axes (each independently).
- G4: Produce reproducible output: same image + same arguments = same data.
- G5: Report an estimated error so users know whether the result is fit for purpose.

## 4. Non-goals

v1:
- Any GUI. The tool is CLI only; review happens through generated PNG overlays.
- Scatter / marker plots (planned v2).
- Batch processing of many figures (planned v3+).
- Bar charts, pie charts, 3D plots, polar plots, ternary plots.
- OCR of tick labels or automatic reading of axis values (the user types the calibration values).
- Direct extraction of vector paths from PDFs (planned v2). v1 always rasterizes.
- Validation / audit-trail features (formal records, signatures, qualification documents).
- Recovering data hidden by overlap or occlusion (the tool flags gaps; it does not invent data).

## 5. Users and use cases

| User | Use case |
|---|---|
| Scientist / engineer | Pull a dose-response, stress-strain or time-course curve from a journal figure into analysis. |
| Data curator | Digitize a few curves from a report or paper, consistently. |

## 6. Approach: how Sobel is used

The Sobel operator convolves the grayscale image with two 3x3 kernels to estimate horizontal and vertical intensity gradients, Gx and Gy. Gradient magnitude `sqrt(Gx^2 + Gy^2)` is high at edges and gradient direction `atan2(Gy, Gx)` gives edge orientation.

Pipeline:

1. **Load and normalize.** Read the PNG, or rasterize the chosen PDF page (default 300 dpi) and crop to the figure. Convert to grayscale, optionally denoise (light Gaussian blur) and upscale small images.
2. **Sobel gradients.** Compute Gx, Gy, magnitude and direction.
3. **Plot-area / axis detection.** Long, strong, near-horizontal and near-vertical edge runs (from Gx and Gy projections) give the axis lines and plot frame. Tick marks are short edge runs perpendicular to the axis, giving candidate tick pixel positions.
4. **Calibration.** Detected ticks are numbered on a preview image. The user assigns data values to two ticks per axis (`--xcal`, `--ycal`), linear or log10. The tool builds the pixel-to-data mapping. Raw pixel coordinates are accepted as a fallback.
5. **Curve candidate extraction.** Inside the plot area, with grid lines and axes masked out, threshold gradient magnitude (Otsu or user-set) and thin to a 1-pixel centerline (non-maximum suppression along the gradient direction, or skeletonization). Candidates are labelled on a candidates image.
6. **Tracing.** The user selects a candidate by label or by a seed pixel/color. The tool follows connected edge pixels, using gradient direction to stay on the same curve through crossings, then resamples to one (x, y) per x column or at a user-set spacing.
7. **Convert and export.** Apply the calibration, write CSV/JSON plus a small sidecar with the arguments used and an overlay PNG.

## 7. CLI workflow

```
vector-trace preview  paper.pdf --page 4 --crop x0,y0,x1,y1   # writes fig.png, ticks.png (numbered ticks)
vector-trace candidates fig.png                                 # writes candidates.png (labelled curves)
vector-trace extract  fig.png --xcal 2:0 7:100 --ycal 1:0 5:1.0 --curve 3 -o curve.csv
vector-trace extract  fig.png --xcal 2:1 7:1000 --xlog ...      # log x axis
```

Each command writes a PNG the user inspects, then reruns with adjusted arguments. The `extract` command also writes `curve.overlay.png` and `curve.json` (sidecar).

## 8. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR1 | Input: PNG, JPG, TIFF, and PDF (page number plus crop box, rasterized at configurable dpi). | Must |
| FR2 | `preview` command: save the Sobel gradient magnitude and a numbered-tick image. | Must |
| FR3 | Auto-detect plot frame and axis lines; override via `--frame x0,y0,x1,y1`. | Must |
| FR4 | Calibrate from numbered ticks (`--xcal tick:value`) or raw pixel positions (`--xcal px:value`). | Must |
| FR5 | Linear and log10 scaling per axis; validate input (log needs values > 0, two distinct values per axis). | Must |
| FR6 | Small tilt correction (up to about 5 degrees) estimated from axis edge angle. | Should |
| FR7 | `candidates` command: label centerline candidates on an image. | Must |
| FR8 | `extract` command: trace the chosen curve (`--curve N`, `--seed x,y`, or `--color`) with Sobel centerline tracing. | Must |
| FR9 | Adjustable parameters: blur, edge threshold, min edge length, sampling spacing. | Must |
| FR10 | Mask grid lines, axes and text regions from candidates. | Should |
| FR11 | Dashed and dotted curves: bridge gaps up to `--max-gap`. | Should |
| FR12 | Exclude regions (`--mask x0,y0,x1,y1`, repeatable) to remove legends, annotations or overlapping series. | Should |
| FR13 | Write an overlay PNG of the extracted curve on the original image. | Must |
| FR14 | Export all extracted curves to one long-format CSV (`series,x,y`). If the combined file can't be written, or `--split` is given, write one CSV per series (`<name>_<series>.csv`) instead and say so on stderr. | Must |
| FR14b | Write a JSON sidecar recording the arguments, image hash and tool version so a run can be repeated. | Should |
| FR15 | Error estimate: pixel size in data units at the calibration, plus the fraction of the trace interpolated across gaps. | Should |
| FR16 | Non-zero exit code and a clear message when axes, ticks or the chosen curve cannot be found. | Must |

## 9. Non-functional requirements

- **Accuracy:** on clean synthetic plots, mean absolute error under 1 pixel (converted to data units) on the traced curve. Error is reported, not just promised.
- **Performance:** under 2 s for gradient computation and tracing of a 2000x1500 image on a standard laptop.
- **Reproducibility:** deterministic output, no randomness.
- **Usability:** a first-time user extracts a clean single curve from a PDF in under 5 minutes using only `--help` and the README.
- **Privacy:** runs fully locally; no image upload.
- **Portability:** Windows first; macOS/Linux should work without code changes.

## 10. Assumptions

- Implementation language is Python (NumPy plus OpenCV or scikit-image; PyMuPDF or pdf2image for PDF rasterization).
- Primary inputs are journal PDFs and PNGs: generally clean, anti-aliased, with visible axes and ticks, and lower noise than scans. JPEG artifacts and photographed pages are secondary.
- Curves are functions of x (one y per x) in v1. Vertical or looping curves are out of scope.
- Calibration values are supplied by the user.

## 11. Success metrics

- Median extraction error under 0.5% of axis span on a benchmark set of at least 30 real figures from journal PDFs, and under 1 pixel on synthetic ones.
- At least 80% of benchmark curves extract correctly within two parameter adjustments.
- Extracting a clean curve takes at least 5x less time than clicking points by hand.
- Re-running with the same sidecar arguments reproduces the output exactly.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Sobel amplifies noise, so JPEG artifacts create false edges. | Pre-blur, adjustable threshold, min-edge-length filter, `preview` saves the edge layer so the user can tune. |
| Thick lines produce two parallel edges (one per side). | Take the midpoint between paired edges or use the skeleton of the filled stroke. |
| Crossing curves and grid lines confuse tracing. | Gradient-direction continuity, color when available, grid masking, `--mask` regions. |
| No GUI means picking a curve and ticks takes a few iterations. | Numbered ticks and labelled candidates images; sensible defaults; clear error messages. |
| Anti-aliasing or low resolution limits accuracy. | Rasterize PDFs at higher dpi; sub-pixel refinement along the gradient direction; report pixel-size error. |
| Wrong calibration silently gives wrong data. | Require two distinct values per axis, print the implied axis range, and always write the overlay for visual confirmation. |
| Colored curves on colored backgrounds have weak grayscale gradients. | Run Sobel on the best channel or on a color-distance map; `--channel` option. |
| Most journal PDFs hold vector plots, where reading the path data directly would beat rasterizing. | Deferred to v2. A spot check of 4 sample PDFs found most figure pages are embedded images; the one mostly-vector paper mixed FEA mesh drawings with charts. |

## 13. Milestones

1. **M1, core pipeline:** PNG input, Sobel, axis and tick detection, calibration, trace one curve, CSV export, overlay PNG.
2. **M2, CLI usability:** PDF input with page and crop, `preview` and `candidates` commands, numbered-tick calibration, `--mask`, clear errors, README.
3. **M3, robustness:** log axes, dashed curves, grid masking, tilt correction, error estimate, sidecar.
4. **M4, benchmark:** synthetic and real figure set, accuracy report.
5. **v2 (later):** scatter / marker plots; direct vector-path extraction from PDFs.
6. **v3+ (later):** batch processing of many figures.

## 14. Decisions and open questions

Decided:
- Interface: CLI only.
- Inputs: journal PDFs and PNGs primarily.
- Validation / audit trail: not required.
- Scatter plots: v2.
- Batch processing: v3+.
- Vector-path extraction from PDFs: v2. v1 is raster/Sobel only.

- Language: Python.
- Output: CSV. One combined file preferred, with one-file-per-series as the fallback (FR14).

Still open:
- None.
