"""Guided calibration: click-then-type instead of read-a-pixel/hand-type-a-flag.

Collects x/y calibration (2 points each, linear or log) and a curve pick (click or
typed color) interactively, then runs the same extraction `extract` would and
prints the equivalent `extract` command as a reproducible record.
"""
import math
import shlex
from pathlib import Path

import cv2

from .colors import match_stroke_color, parse_color
from .core import find_frame, overlay, plot_roi, sobel_magnitude, to_data, trace_pixels, write_csv

ESC = 27


class _Cancelled(Exception):
    """Esc was pressed; unwinds to run_wizard(), which turns this into a clean cancel."""


def format_cal_pair(px, value):
    """One calibration point as "PIXEL:VALUE", the syntax --xcal/--ycal take."""
    return f"{int(round(px))}:{float(value):.10g}"


def parse_typed_value(text, log):
    """A terminal-typed calibration value: numeric, and > 0 if the axis is log."""
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"not a number: {text!r}")
    if not math.isfinite(value):
        raise ValueError(f"not a finite number: {text!r}")
    if log and value <= 0:
        raise ValueError("log axis needs a value > 0")
    return value


def build_command(image, xcal_pairs, ycal_pairs, xlog, ylog, seed=None, color=None, output="curve.csv"):
    """The `vector-trace extract ...` command equivalent to the calibration/curve pick just collected."""
    parts = ["vector-trace", "extract", shlex.quote(str(image))]
    parts += ["--xcal", *(format_cal_pair(px, v) for px, v in xcal_pairs)]
    parts += ["--ycal", *(format_cal_pair(px, v) for px, v in ycal_pairs)]
    if xlog:
        parts.append("--xlog")
    if ylog:
        parts.append("--ylog")
    if seed is not None:
        parts += ["--seed", f"{seed[0]},{seed[1]}"]
    elif color is not None:
        parts += ["--color", shlex.quote(color)]
    parts += ["-o", shlex.quote(str(output))]
    return " ".join(parts)


def _ask_yes_no(prompt):
    return input(prompt).strip().lower().startswith("y")


def _prompt_for_value(label, log):
    while True:
        text = input(f"value at {label}: ").strip()
        try:
            return parse_typed_value(text, log)
        except ValueError as err:
            print(f"  {err}; try again")


def _prompt_for_color():
    while True:
        text = input("color name or hex (e.g. 'blue' or '#1f77b4'): ").strip()
        try:
            parse_color(text)
            return text
        except ValueError as err:
            print(f"  {err}; try again")


def _mark(img, x, y, label):
    cv2.circle(img, (x, y), 4, (0, 255, 255), -1)
    cv2.putText(img, label, (x + 6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)


def _banner(img, lines):
    shown = img.copy()
    h = 24 * len(lines) + 6
    w = 6 + max(len(line) for line in lines) * 11
    cv2.rectangle(shown, (0, 0), (w, h), (0, 0, 0), -1)
    for i, line in enumerate(lines):
        cv2.putText(shown, line, (6, 24 * i + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return shown


def _wait_for_click(win, base, banner_lines, extra_keys=()):
    """Show base+banner, poll until a left click or Esc (or one of extra_keys).

    Returns the click (x, y), or whichever member of extra_keys was pressed.
    """
    state = {"click": None}

    def _on_mouse(event, x, y, flags, userdata):
        if event == cv2.EVENT_LBUTTONDOWN:
            state["click"] = (x, y)

    cv2.setMouseCallback(win, _on_mouse)
    cv2.imshow(win, _banner(base, banner_lines))
    while state["click"] is None:
        key = cv2.waitKey(50) & 0xFF
        if key == ESC:
            raise _Cancelled()
        if key in extra_keys:
            return key
    return state["click"]


def run_wizard(image_path, output="curve.csv"):
    """Run the guided flow end-to-end. Returns the extracted points, or None if cancelled."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"cannot read image: {image_path}")
    frame = find_frame(sobel_magnitude(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)))

    win = f"vector-trace guide: {image_path}  (Esc to cancel)"
    try:
        cv2.imshow(win, _banner(img, ["vector-trace guide", "answer the prompts in your terminal, then click to calibrate"]))
        cv2.waitKey(1)
    except cv2.error as err:
        raise ValueError(
            "cv2.imshow has no GUI support (opencv-python-headless is installed); "
            "run 'pip install opencv-python' to use guide"
        ) from err

    try:
        xlog = _ask_yes_no("Log x-axis? Data values are powers of ten spacing. [y/N]: ")
        ylog = _ask_yes_no("Log y-axis? Data values are powers of ten spacing. [y/N]: ")

        marks, xcal, ycal = [], [], []
        steps = [("x", 1, xlog, xcal), ("x", 2, xlog, xcal), ("y", 1, ylog, ycal), ("y", 2, ylog, ycal)]
        for i, (axis, n, log, cal) in enumerate(steps, 1):
            label = f"{axis.upper()}{n}"
            base = img.copy()
            for mx, my, mlabel in marks:
                _mark(base, mx, my, mlabel)
            banner = [f"CALIBRATION {i}/4 -- click {axis.upper()}-AXIS POINT {n}", "then type its value in the terminal"]
            cx, cy = _wait_for_click(win, base, banner)
            marks.append((cx, cy, label))
            confirmed = img.copy()
            for mx, my, mlabel in marks:
                _mark(confirmed, mx, my, mlabel)
            cv2.imshow(win, _banner(confirmed, [f"{label} = pixel {cx},{cy}"]))
            cv2.waitKey(1)
            value = _prompt_for_value(f"{label} ({'log' if log else 'linear'} axis)", log)
            cal.append((cx if axis == "x" else cy, value))

        base = img.copy()
        for mx, my, mlabel in marks:
            _mark(base, mx, my, mlabel)
        banner = ["CURVE -- click the curve to trace", "or press 'c' to type a color name/hex instead"]
        result = _wait_for_click(win, base, banner, extra_keys={ord("c"), ord("C")})
        seed = color_spec = None
        if isinstance(result, tuple):
            seed = result
            print(f"curve seed: pixel {seed[0]},{seed[1]}")
        else:
            color_spec = _prompt_for_color()
    except (_Cancelled, KeyboardInterrupt, EOFError):
        cv2.destroyAllWindows()
        print("cancelled; nothing written")
        return None

    cv2.destroyAllWindows()

    color_bgr = match_stroke_color(img, plot_roi(img.shape[:2], frame), color_spec) if color_spec else None
    cols, rows = trace_pixels(str(image_path), seed, color_bgr, frame)
    pts = to_data(cols, rows, xcal, ycal, xlog, ylog)

    out_path = Path(output)
    write_csv(out_path, pts)
    cv2.imwrite(str(out_path.with_suffix(".overlay.png")), overlay(img, frame, cols, rows))
    print(f"{len(pts)} points -> {out_path}")
    print(build_command(image_path, xcal, ycal, xlog, ylog, seed=seed, color=color_spec, output=out_path))
    return pts
