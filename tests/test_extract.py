import subprocess
import sys

import numpy as np
import pytest
from synthetic import make_plot

from vector_trace.core import extract_curve

MAX_ERR_PX = 2.5


def _y_pixel(ycal):
    (p0, v0), (p1, v1) = ycal
    return abs((v1 - v0) / (p1 - p0))


def _check(tmp_path, kind, xlog):
    png = tmp_path / "fig.png"
    s = make_plot(png, kind)
    pts = extract_curve(png, s["xcal"], s["ycal"], xlog=xlog)
    lo, hi = s["x_range"]
    span = (hi / lo) if xlog else (hi - lo)
    inner = (pts[:, 0] > (lo * span**0.03 if xlog else lo + 0.03 * span)) & (
        pts[:, 0] < (hi / span**0.03 if xlog else hi - 0.03 * span)
    )
    err = np.abs(pts[inner, 1] - s["truth"](pts[inner, 0]))
    assert err.max() < MAX_ERR_PX * _y_pixel(s["ycal"])
    return pts, s


def test_linear(tmp_path):
    pts, s = _check(tmp_path, "linear", xlog=False)
    assert pts[:, 0].max() - pts[:, 0].min() > 0.9 * 10


def test_logx(tmp_path):
    _check(tmp_path, "logx", xlog=True)


@pytest.mark.xfail(reason="dashed curves need gap bridging (M3)", strict=False)
def test_dashed_covers_x_range(tmp_path):
    pts, _ = _check(tmp_path, "dashed", xlog=False)
    assert pts[:, 0].max() - pts[:, 0].min() > 0.9 * 10


def test_bad_calibration(tmp_path):
    png = tmp_path / "fig.png"
    s = make_plot(png)
    with pytest.raises(ValueError):
        extract_curve(png, [(100, 1.0), (100, 2.0)], s["ycal"])
    with pytest.raises(ValueError):
        extract_curve(png, [(100, -1.0), (200, 2.0)], s["ycal"], xlog=True)


def test_cli_end_to_end(tmp_path):
    png, out = tmp_path / "fig.png", tmp_path / "curve.csv"
    s = make_plot(png)
    xc = [f"{p}:{v}" for p, v in s["xcal"]]
    yc = [f"{p}:{v}" for p, v in s["ycal"]]
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "extract", str(png), "--xcal", *xc, "--ycal", *yc, "-o", str(out)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    lines = out.read_text().splitlines()
    assert lines[0] == "series,x,y" and len(lines) > 50
    assert out.with_suffix(".overlay.png").exists()


def test_extract_curve_by_color(tmp_path):
    png = tmp_path / "fig.png"
    s = make_plot(png)  # black curve
    pts = extract_curve(png, s["xcal"], s["ycal"], color=(0, 0, 0))
    assert pts[:, 0].max() - pts[:, 0].min() > 0.9 * 10


def _px_for(cal, val):
    (p0, v0), (p1, v1) = cal
    return round(p0 + (val - v0) * (p1 - p0) / (v1 - v0))


def test_cli_color_matches_seed(tmp_path):
    png = tmp_path / "fig.png"
    s = make_plot(png)
    xc = [f"{p}:{v}" for p, v in s["xcal"]]
    yc = [f"{p}:{v}" for p, v in s["ycal"]]
    x_mid = sum(s["x_range"]) / 2
    seed = f"{_px_for(s['xcal'], x_mid)},{_px_for(s['ycal'], s['truth'](x_mid))}"

    out_color, out_seed = tmp_path / "color.csv", tmp_path / "seed.csv"
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "extract", str(png), "--xcal", *xc, "--ycal", *yc, "--color", "black", "-o", str(out_color)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "black" not in r.stdout and "#" not in r.stdout  # no dominant-color listing printed

    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "extract", str(png), "--xcal", *xc, "--ycal", *yc, "--seed", seed, "-o", str(out_seed)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out_color.read_text() == out_seed.read_text()


def test_cli_color_rejects_bad_name(tmp_path):
    png = tmp_path / "fig.png"
    s = make_plot(png)
    xc = [f"{p}:{v}" for p, v in s["xcal"]]
    yc = [f"{p}:{v}" for p, v in s["ycal"]]
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "extract", str(png), "--xcal", *xc, "--ycal", *yc, "--color", "not-a-color"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
    assert "not-a-color" in r.stderr


def test_cli_seed_and_color_mutually_exclusive(tmp_path):
    png = tmp_path / "fig.png"
    s = make_plot(png)
    xc = [f"{p}:{v}" for p, v in s["xcal"]]
    yc = [f"{p}:{v}" for p, v in s["ycal"]]
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "extract", str(png), "--xcal", *xc, "--ycal", *yc, "--seed", "1,1", "--color", "black"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
