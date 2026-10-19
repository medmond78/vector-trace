import argparse
import csv
import pydoc
import sys
from pathlib import Path

import cv2
import numpy as np

from .colors import dominant_colors, match_stroke_color, nearest_color_name, nearest_emoji
from .core import find_frame, plot_roi, sobel_magnitude, to_data, trace_pixels
from .man import MAN

for _stream in (sys.stdout, sys.stderr):  # the man text and `colors` output contain emoji; Windows consoles default to cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


class _Man(argparse.Action):
    def __init__(self, option_strings, dest, **kw):
        super().__init__(option_strings, dest, nargs=0, default=argparse.SUPPRESS, help="show the full manual and exit")

    def __call__(self, parser, namespace, values, option_string=None):
        pydoc.pager(MAN) if sys.stdout.isatty() else print(MAN)
        parser.exit()


def _cal(items):
    try:
        return [tuple(float(t) for t in s.split(":")) for s in items]
    except ValueError:
        raise SystemExit(f"bad calibration {items}; expected PIXEL:VALUE PIXEL:VALUE")


def _pair(s):
    return tuple(float(t) for t in s.split(","))


def _frame(a, img):
    if not a.frame:
        return find_frame(sobel_magnitude(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)))
    frame = tuple(int(v) for v in _pair(a.frame))
    if len(frame) != 4:
        raise ValueError("--frame needs X0,Y0,X1,Y1")
    return frame


def _overlay(img, frame, cols, rows):
    x0, y0, x1, y1 = (int(v) for v in frame)
    cv2.rectangle(img, (x0, y0), (x1, y1), (0, 160, 0), 1)
    cv2.polylines(img, [np.round(np.column_stack([cols, rows])).astype(np.int32)], False, (0, 0, 255), 1)
    return img


def extract(a):
    xcal, ycal = _cal(a.xcal), _cal(a.ycal)
    img = cv2.imread(a.image)
    if img is None:
        raise ValueError(f"cannot read image: {a.image}")
    frame = _frame(a, img)
    color = match_stroke_color(img, plot_roi(img.shape[:2], frame), a.color) if a.color else None
    cols, rows = trace_pixels(a.image, a.seed and _pair(a.seed), color, frame, a.thr, a.tol)
    pts = to_data(cols, rows, xcal, ycal, a.xlog, a.ylog)

    out = Path(a.output)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["series", "x", "y"])
        w.writerows(("curve1", f"{x:.10g}", f"{y:.10g}") for x, y in pts)

    cv2.imwrite(str(out.with_suffix(".overlay.png")), _overlay(img, frame, cols, rows))
    print(f"{len(pts)} points -> {out}")


def colors(a):
    img = cv2.imread(a.image)
    if img is None:
        raise ValueError(f"cannot read image: {a.image}")
    roi = plot_roi(img.shape[:2], _frame(a, img))
    for rgb, frac in dominant_colors(img, roi, a.n):
        print(f"{nearest_emoji(rgb)}  #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}  {nearest_color_name(rgb)}  {frac:.0%}")


def preview(a):
    if not 0 <= a.opacity <= 100:
        raise ValueError("opacity must be between 0 and 100")
    img = cv2.imread(a.image)
    if img is None:
        raise ValueError(f"cannot read image: {a.image}")
    frame = _frame(a, img)
    color = match_stroke_color(img, plot_roi(img.shape[:2], frame), a.color) if a.color else None
    cols, rows = trace_pixels(a.image, a.seed and _pair(a.seed), color, frame, a.thr, a.tol)
    faded = (img.astype(np.float32) * (a.opacity / 100.0)).astype(np.uint8)
    _overlay(faded, frame, cols, rows)
    win = f"vector-trace preview: {a.image}  (press any key to close)"

    def _show_pixel(event, x, y, flags, userdata):
        if event != cv2.EVENT_MOUSEMOVE:
            return
        shown = faded.copy()
        cv2.rectangle(shown, (0, 0), (150, 24), (0, 0, 0), -1)
        cv2.putText(shown, f"{x},{y}", (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(win, shown)

    try:
        cv2.imshow(win, faded)
        cv2.setMouseCallback(win, _show_pixel)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except cv2.error as err:
        raise ValueError(
            "cv2.imshow has no GUI support (opencv-python-headless is installed); "
            "run 'pip install opencv-python' to use preview"
        ) from err
    print(f"{len(cols)} points traced (preview only; nothing written)")


EXAMPLES = """\
examples:
  vector-trace extract fig.png --xcal 193:0 1052:12 --ycal 653.5:0 88.5:140 -o curve.csv
  vector-trace extract fig.png --xcal 193:0 1052:12 --ycal 653.5:0 88.5:140 --seed 908,335
  vector-trace extract fig.png --xcal 193:0 1052:12 --ycal 653.5:0 88.5:140 --color "#1f77b4"
  vector-trace extract fig.png --xcal 253.5:10 546.5:100 --xlog --ycal 471.5:10 66.5:50

pixel coordinates are pixel indices (origin top-left; y is the row).
run with --man for the full manual.
"""


def main(argv=None):
    fmt = argparse.RawDescriptionHelpFormatter
    p = argparse.ArgumentParser(
        prog="vector-trace",
        formatter_class=fmt,
        description="Digitize a curve from an image of a 2D plot using Sobel edge detection.",
        epilog="run 'vector-trace --man' for the full manual.",
    )
    p.add_argument("--man", action=_Man)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser(
        "extract",
        formatter_class=fmt,
        help="trace one curve and write CSV + overlay PNG",
        description="Trace one curve and write a CSV and an overlay PNG.",
        epilog=EXAMPLES,
    )
    e.add_argument("--man", action=_Man)
    e.add_argument("image")
    e.add_argument("--xcal", nargs=2, required=True, metavar="PX:VAL", help="two x-axis calibration points")
    e.add_argument("--ycal", nargs=2, required=True, metavar="PY:VAL", help="two y-axis calibration points")
    eg = e.add_mutually_exclusive_group()
    eg.add_argument("--seed", metavar="X,Y", help="pixel on the target curve; traces the stroke of that color (default: widest edge curve)")
    eg.add_argument("--color", metavar="NAME|HEX", help="trace the curve whose stroke best matches this common color name or hex code (e.g. 'blue' or '#1f77b4'), instead of a pixel seed")
    e.add_argument("--tol", type=float, default=40, help="with --seed/--color: color tolerance (RGB distance, default 40)")
    e.add_argument("--frame", metavar="X0,Y0,X1,Y1", help="plot area in pixels (default: auto-detect)")
    e.add_argument("--thr", type=float, default=0.3, help="without --seed/--color: edge threshold, fraction of max gradient (default 0.3)")
    e.add_argument("--xlog", action="store_true", help="log10 x axis")
    e.add_argument("--ylog", action="store_true", help="log10 y axis")
    e.add_argument("-o", "--output", default="curve.csv", help="output CSV (default curve.csv)")
    c = sub.add_parser(
        "colors",
        formatter_class=fmt,
        help="list the plot's dominant colors (no curve extraction)",
        description="Identify the plot's dominant stroke colors and print each one's hex code, "
        "nearest common color name, and a matching color-square emoji. Does not extract curve data.",
    )
    c.add_argument("--man", action=_Man)
    c.add_argument("image")
    c.add_argument("--n", type=int, default=5, help="number of dominant colors to report (default 5)")
    c.add_argument("--frame", metavar="X0,Y0,X1,Y1", help="plot area in pixels (default: auto-detect)")
    v = sub.add_parser(
        "preview",
        formatter_class=fmt,
        help="show the traced curve in a window (writes nothing to disk)",
        description="Trace one curve and show it, overlaid on the image, in a window. Writes no files.",
    )
    v.add_argument("--man", action=_Man)
    v.add_argument("image")
    v.add_argument(
        "opacity",
        nargs="?",
        type=int,
        default=40,
        metavar="OPACITY",
        help="opacity of the original image under the overlay, 0-100 (default 40); 0 fades it to black, 100 is full strength",
    )
    vg = v.add_mutually_exclusive_group()
    vg.add_argument("--seed", metavar="X,Y", help="pixel on the target curve; traces the stroke of that color (default: widest edge curve)")
    vg.add_argument("--color", metavar="NAME|HEX", help="trace the curve whose stroke best matches this common color name or hex code (e.g. 'blue' or '#1f77b4'), instead of a pixel seed")
    v.add_argument("--tol", type=float, default=40, help="with --seed/--color: color tolerance (RGB distance, default 40)")
    v.add_argument("--frame", metavar="X0,Y0,X1,Y1", help="plot area in pixels (default: auto-detect)")
    v.add_argument("--thr", type=float, default=0.3, help="without --seed/--color: edge threshold, fraction of max gradient (default 0.3)")
    a = p.parse_args(argv)
    try:
        {"extract": extract, "colors": colors, "preview": preview}[a.cmd](a)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0
