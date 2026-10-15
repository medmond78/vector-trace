import argparse
import csv
import pydoc
import sys
from pathlib import Path

import cv2
import numpy as np

from .core import find_frame, sobel_magnitude, to_data, trace_pixels
from .man import MAN


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


def extract(a):
    xcal, ycal = _cal(a.xcal), _cal(a.ycal)
    img = cv2.imread(a.image)
    if img is None:
        raise ValueError(f"cannot read image: {a.image}")
    if a.frame:
        frame = tuple(int(v) for v in _pair(a.frame))
        if len(frame) != 4:
            raise ValueError("--frame needs X0,Y0,X1,Y1")
    else:
        frame = find_frame(sobel_magnitude(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)))
    cols, rows = trace_pixels(a.image, a.seed and _pair(a.seed), frame, a.thr, a.tol)
    pts = to_data(cols, rows, xcal, ycal, a.xlog, a.ylog)

    out = Path(a.output)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["series", "x", "y"])
        w.writerows(("curve1", f"{x:.10g}", f"{y:.10g}") for x, y in pts)

    x0, y0, x1, y1 = (int(v) for v in frame)
    cv2.rectangle(img, (x0, y0), (x1, y1), (0, 160, 0), 1)
    cv2.polylines(img, [np.round(np.column_stack([cols, rows])).astype(np.int32)], False, (0, 0, 255), 1)
    cv2.imwrite(str(out.with_suffix(".overlay.png")), img)
    print(f"{len(pts)} points -> {out}")


EXAMPLES = """\
examples:
  vector-trace extract fig.png --xcal 193:0 1052:12 --ycal 653.5:0 88.5:140 -o curve.csv
  vector-trace extract fig.png --xcal 193:0 1052:12 --ycal 653.5:0 88.5:140 --seed 908,335
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
    e.add_argument("--seed", metavar="X,Y", help="pixel on the target curve; traces the stroke of that color (default: widest edge curve)")
    e.add_argument("--tol", type=float, default=40, help="with --seed: color tolerance (RGB distance, default 40)")
    e.add_argument("--frame", metavar="X0,Y0,X1,Y1", help="plot area in pixels (default: auto-detect)")
    e.add_argument("--thr", type=float, default=0.3, help="without --seed: edge threshold, fraction of max gradient (default 0.3)")
    e.add_argument("--xlog", action="store_true", help="log10 x axis")
    e.add_argument("--ylog", action="store_true", help="log10 y axis")
    e.add_argument("-o", "--output", default="curve.csv", help="output CSV (default curve.csv)")
    a = p.parse_args(argv)
    try:
        extract(a)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0
