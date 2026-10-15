# vector-trace

Command-line tool that digitizes a curve from an image of a 2D plot. It uses Sobel edge detection to find the plot area and the curve, then converts pixel positions to data values using two reference points you give for each axis.

Output is a CSV of (x, y) points and an overlay image for checking the trace by eye.

Status: early (M1 plus seed-color tracing). Raster images only, one curve per run. See `PRD.md` for the design and roadmap.

## Install

Developed and tested on Python 3.13.

```
python -m venv .vector_trace
source .vector_trace/Scripts/activate      # Git Bash; on cmd: .vector_trace\Scripts\activate
pip install numpy opencv-python-headless
```

Run from the repo root as `python -m vector_trace ...`.

## Quick start

```
python -m vector_trace extract fig.png \
    --xcal 193:0 1052:12 \
    --ycal 653.5:0 88.5:140 \
    -o curve.csv
```

This writes `curve.csv` and `curve.overlay.png`. Open the overlay and confirm the red line sits on your curve before using the numbers.

## Workflow

1. **Get an image.** PNG, JPG, TIFF or BMP. For a figure in a PDF, export or screenshot it at the highest resolution you can. Higher resolution means a smaller pixel size in data units.
2. **Find two reference points per axis.** Open the image in a viewer that shows the cursor position (Paint, GIMP, ImageJ/Fiji) and note the pixel position of two grid lines or ticks on each axis, as far apart as possible. Write each as `PIXEL:VALUE`:
   - x axis: pixel is the column number
   - y axis: pixel is the row number (counted from the top)
   - Pixel coordinates are pixel indices: origin top-left, pixel centers at integers.
3. **Run `extract`** with `--xcal` and `--ycal`.
4. **Check the overlay** (green rectangle = detected plot area, red = traced curve).
5. **Adjust** if needed (see below).

## Choosing a curve: `--seed`

Without `--seed`, the tool traces the widest edge shape in the plot area. That works for one clean curve.

With several curves, markers or annotations, give a pixel on the curve you want:

```
python -m vector_trace extract fig.png --xcal 193:0 1052:12 --ycal 653.5:0 88.5:140 \
    --seed 908,335 -o blue.csv
```

The seed is `column,row`, within 10 pixels of the curve. The tool takes the stroke color there and traces only that color. This separates curves, ignores markers of another color, and stays off grid lines. Run once per curve.

If the trace breaks up along the curve, raise `--tol` (default 40). If it jumps onto a similar-colored neighbor, lower it.

## Log axes

Add `--xlog` and/or `--ylog` and give the real (positive) values:

```
python -m vector_trace extract fig.png --xcal 253.5:10 546.5:100 --xlog \
    --ycal 471.5:10 66.5:50 -o curve.csv
```

## If the plot area is wrong

The plot area is detected from the long, dark axis lines. A dark grid or an unusual frame can fool it. Override it with the inner corners of the axes:

```
--frame X0,Y0,X1,Y1
```

## Output

`curve.csv`:

```
series,x,y
curve1,0.1,4.8
curve1,0.2,6.1
...
```

One row per image column the curve covers, sorted by x. `curve.overlay.png` is written next to it.

Exit code is 0 on success, 1 with a message on stderr for a bad image, bad calibration, no curve found, or a seed that is not on a curve.

## Help

```
python -m vector_trace --help
python -m vector_trace extract --help
python -m vector_trace --man          # full manual
```

## Limitations

- One curve per run, and the curve must be a function of x (one y per x).
- Dashed and dotted curves: only the dash under the seed is traced.
- Where one curve is drawn over another, the hidden part is missing.
- About 3 pixels at each end of a curve that meets an axis are lost.
- Very light strokes (close to white) cannot be seeded.
- Accuracy on clean images is about one pixel. It depends on how precisely you place the calibration points.
- Scatter plots, direct PDF input, and batch processing are planned for later versions (see `PRD.md`).

## Tests

```
pip install matplotlib pytest
python -m pytest tests -q
```

The synthetic-plot tests generate their own images. The real-figure tests in `tests/test_real.py` need the example figures in `tests/` and are skipped if they are missing.

## License

MIT, see `LICENSE`.
