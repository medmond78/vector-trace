"""Sobel-based curve extraction from a raster plot image.

Pixel coordinates are pixel indices (pixel centers at integers, origin top-left).
Without a seed the curve is found from Sobel edges; with a seed it is found by the
stroke color at the seed (needed to separate curves, markers and annotations).
"""
import cv2
import numpy as np

AXIS_MARGIN = 3  # px kept clear of the axis lines when searching for the curve
SEED_RADIUS = 10  # px: how far from the seed a curve pixel may be
INK_DIST = 120  # min RGB distance from white for a pixel to count as stroke (grid lines are lighter)


def sobel_magnitude(gray):
    g = cv2.GaussianBlur(gray, (3, 3), 0)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def _inner_span(idx, n):
    """Inner edges of the axis lines found at indices idx along an image side of length n."""
    if len(idx) == 0:
        return 0, n - 1
    gaps = np.diff(idx)
    if len(gaps) and gaps.max() > 0.1 * n:
        k = gaps.argmax()
        return int(idx[k]), int(idx[k + 1])
    # only one axis line: assume the plot area extends from it to the image edge
    return (int(idx.max()), n - 1) if idx.mean() < n / 2 else (0, int(idx.min()))


def find_frame(mag):
    """Plot area (x0, y0, x1, y1) between the axis lines, from long strong edge runs.

    shortcut: assumes axis lines are the only long strong edges (no dark grid), override with frame=
    """
    strong = mag > 0.5 * mag.max()
    cols, rows = strong.sum(0), strong.sum(1)
    xs = np.flatnonzero(cols >= 0.6 * cols.max())
    ys = np.flatnonzero(rows >= 0.6 * rows.max())
    x0, x1 = _inner_span(xs, mag.shape[1])
    y0, y1 = _inner_span(ys, mag.shape[0])
    return x0, y0, x1, y1


def _seed_color(bgr, seed, roi):
    """Core stroke color (BGR float) of the curve pixel nearest the seed."""
    dist = np.linalg.norm(255.0 - bgr, axis=2)
    rr, cc = np.nonzero((dist > INK_DIST) & roi)
    if len(rr) == 0:
        raise ValueError("no stroke pixels in the plot area")
    d2 = (cc - seed[0]) ** 2 + (rr - seed[1]) ** 2
    k = int(d2.argmin())
    if d2[k] > SEED_RADIUS**2:
        raise ValueError(f"no curve within {SEED_RADIUS} px of seed {seed}")
    y, x = int(rr[k]), int(cc[k])
    ys, xs = max(y - 3, 0), max(x - 3, 0)
    win = dist[ys : y + 4, xs : x + 4]
    j, i = np.unravel_index(win.argmax(), win.shape)  # most saturated pixel = anti-aliasing free
    return bgr[ys + j, xs + i].astype(np.float32)


def _color_mask(bgr, color, tol, tmin=0.4, tmax=1.15):
    """Stroke pixels of `color`: exact-color core plus anti-aliased edge pixels (blends of color and white) touching the core.

    Requiring the core to match keeps similar-hue curves apart; t > tmax rejects strokes darker than the seed.
    """
    core = np.linalg.norm(bgr.astype(np.float32) - color, axis=2) < tol / 2
    d = color - 255.0
    v = bgr.astype(np.float32) - 255.0
    t = (v @ d) / float(d @ d)
    res = np.linalg.norm(v - t[..., None] * d, axis=2)
    edge = (t >= tmin) & (t <= tmax) & (res < tol)
    near_core = cv2.dilate(core.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    return core | (edge & near_core)


def plot_roi(shape, frame):
    """Boolean mask of `shape` covering the plot area `frame`, kept AXIS_MARGIN px off the axis lines."""
    x0, y0, x1, y1 = frame
    roi = np.zeros(shape, bool)
    roi[y0 + AXIS_MARGIN : y1 - AXIS_MARGIN + 1, x0 + AXIS_MARGIN : x1 - AXIS_MARGIN + 1] = True
    return roi


def trace_pixels(image_path, seed=None, color=None, frame=None, thr=0.3, tol=40):
    """Trace one curve. Returns (cols, rows) float arrays in pixel indices, one point per image column.

    seed=None, color=None: the widest Sobel-edge component.
    seed=(x, y): the stroke of the color at that pixel, nearest to the seed.
    color=(b, g, r): the widest stroke of that exact color (no pixel needed to disambiguate it).
    """
    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"cannot read image: {image_path}")
    mag = sobel_magnitude(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    frame = frame if frame is not None else find_frame(mag)
    roi = plot_roi(mag.shape, frame)
    if not roi.any() or not mag[roi].any():
        raise ValueError("plot area is empty; pass frame=x0,y0,x1,y1")

    if seed is None and color is None:
        binary = (mag > thr * mag[roi].max()) & roi
        closed = binary
    else:
        target = np.asarray(color, dtype=np.float32) if color is not None else _seed_color(bgr, seed, roi)
        binary = _color_mask(bgr, target, tol) & roi
        # bridge the few pixels a marker or crossing line hides from the stroke
        closed = cv2.morphologyEx(binary.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
    n, labels, stats, _ = cv2.connectedComponentsWithStats(closed.astype(np.uint8), connectivity=8)
    if n < 2:
        raise ValueError("no curve found inside the plot area; try a lower threshold")

    if seed is None:
        lab = 1 + int(stats[1:, cv2.CC_STAT_WIDTH].argmax())
    else:
        rr, cc = np.nonzero(binary)
        d2 = (cc - seed[0]) ** 2 + (rr - seed[1]) ** 2
        k = int(d2.argmin())
        if d2[k] > SEED_RADIUS**2:
            raise ValueError(f"no curve within {SEED_RADIUS} px of seed {seed}")
        lab = int(labels[rr[k], cc[k]])
    rr, cc = np.nonzero((labels == lab) & binary)
    cols = np.unique(cc)
    # shortcut: one y per column (mean of the stroke/edge band), so curves must be functions of x
    rows = np.array([rr[cc == c].mean() for c in cols])
    return cols.astype(float), rows


def _axis_map(cal, log, name):
    (p0, v0), (p1, v1) = cal
    if p0 == p1 or v0 == v1:
        raise ValueError(f"{name} calibration needs two distinct pixels and two distinct values")
    if log:
        if v0 <= 0 or v1 <= 0:
            raise ValueError(f"{name} log axis needs values > 0")
        v0, v1 = np.log10(v0), np.log10(v1)
    k = (v1 - v0) / (p1 - p0)

    def f(p):
        v = v0 + (np.asarray(p, float) - p0) * k
        return 10**v if log else v

    return f


def to_data(cols, rows, xcal, ycal, xlog=False, ylog=False):
    fx = _axis_map(xcal, xlog, "x")
    fy = _axis_map(ycal, ylog, "y")
    return np.column_stack([fx(cols), fy(rows)])


def extract_curve(image_path, xcal, ycal, seed=None, color=None, xlog=False, ylog=False, frame=None, thr=0.3, tol=40):
    """xcal=[(px, value)]*2, ycal=[(py, value)]*2. Returns (N, 2) data points sorted by x."""
    cols, rows = trace_pixels(image_path, seed, color, frame, thr, tol)
    pts = to_data(cols, rows, xcal, ycal, xlog, ylog)
    return pts[np.argsort(pts[:, 0])]
