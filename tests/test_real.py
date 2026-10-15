"""Regression tests on real journal figures (seeded color tracing).

Calibrations are grid-line pixel positions measured once. Expected values for test1/test3
are read off the figures (tolerances are loose); test2 has no y labels, so its y axis uses
arbitrary decades and its expected values are golden outputs (regression only, not accuracy).
"""
from pathlib import Path

import numpy as np
import pytest

from vector_trace.core import extract_curve, to_data, trace_pixels

HERE = Path(__file__).parent

T1 = dict(image="test1.png", xcal=[(193.0, 0), (1052.0, 12)], ycal=[(653.5, 0), (88.5, 140)])
T2 = dict(image="test2.png", xcal=[(181.5, 0.65), (737.5, 0.95)], ycal=[(484.5, 1), (110.5, 1e4)], ylog=True)
T3 = dict(image="test3_with_points.png", xcal=[(253.5, 10), (546.5, 100)], ycal=[(471.5, 10), (66.5, 50)], xlog=True)

# id, setup, seed, expected (x, y, tol) [tol: absolute, or log10 decades when ylog], x range covered, max px jump per column
CASES = [
    ("t1_blue", T1, (908, 335), [(5.5, 102.5, 2), (10, 79, 2.5), (11.5, 73, 2)], (0.5, 11.5), 6),
    ("t1_cyan", T1, (908, 113), [(7.9, 146.3, 2), (10, 134, 2.5), (11.5, 124.5, 2)], (2.0, 11.5), 6),
    ("t3_model", T3, (190, 405), [(10, 20.5, 1), (100, 38.5, 1), (900, 46.5, 1)], (5.5, 900), 3),
]
# test2: five curves, seeded at one image column; golden y (arbitrary decades) at x=0.7 and 0.8
for r, ys, xmax in (
    (122, (7411, 666), 0.99),
    (180, (1777, 158), 0.99),
    (245, (355, 31.8), 0.98),
    (311, (71.4, 6.4), 0.95),
    (376, (14.3, 1.28), 0.90),
):
    CASES.append((f"t2_row{r}", T2, (274, r), [(0.7, ys[0], 0.05), (0.8, ys[1], 0.05)], (0.62, xmax), 6))


def _run(setup, seed):
    path = HERE / setup["image"]
    if not path.exists():
        pytest.skip(f"{path.name} not present")
    kw = {k: v for k, v in setup.items() if k != "image"}
    return path, kw


@pytest.mark.parametrize("name,setup,seed,expected,xrange,max_jump", CASES, ids=[c[0] for c in CASES])
def test_real_figure(name, setup, seed, expected, xrange, max_jump):
    path, kw = _run(setup, seed)
    pts = extract_curve(path, seed=seed, **kw)
    assert pts[0, 0] <= xrange[0] and pts[-1, 0] >= xrange[1]
    ylog = kw.get("ylog", False)
    for x, y, tol in expected:
        got = np.interp(x, pts[:, 0], pts[:, 1])
        err = abs(np.log10(got / y)) if ylog else abs(got - y)
        assert err < tol, f"{name}: y({x}) = {got:.4g}, expected {y} (err {err:.3g} > {tol})"


@pytest.mark.parametrize("name,setup,seed,expected,xrange,max_jump", CASES, ids=[c[0] for c in CASES])
def test_real_figure_has_no_spikes(name, setup, seed, expected, xrange, max_jump):
    # catches the trace jumping onto a neighbouring curve, marker or annotation
    path, kw = _run(setup, seed)
    cols, rows = trace_pixels(path, seed=seed)
    # shortcut: steep curve ends (right of the last expected x) are exempt
    last = to_data(cols, rows, kw["xcal"], kw["ycal"], kw.get("xlog", False), kw.get("ylog", False))[:, 0]
    keep = last <= xrange[1]
    jumps = np.abs(np.diff(rows[keep]))[np.diff(cols[keep]) == 1]
    assert jumps.max() <= max_jump, f"{name}: {jumps.max():.1f} px jump between adjacent columns"


def test_seed_off_curve_is_an_error():
    path = HERE / "test3_with_points.png"
    if not path.exists():
        pytest.skip("test3_with_points.png not present")
    with pytest.raises(ValueError, match="no curve within"):
        extract_curve(path, T3["xcal"], T3["ycal"], seed=(500, 520), xlog=True)  # empty area near the x axis
