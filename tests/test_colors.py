import subprocess
import sys

import cv2
import pytest
from synthetic import make_plot

from vector_trace.colors import match_stroke_color, nearest_color_name, nearest_emoji, parse_color
from vector_trace.core import find_frame, plot_roi, sobel_magnitude


def test_nearest_name_and_emoji():
    assert nearest_color_name((10, 10, 10)) == "black"
    assert nearest_emoji((10, 10, 10)) == "⬛"
    assert nearest_emoji((0, 0, 230)) == "🟦"


def test_parse_color():
    assert parse_color("black") == (0, 0, 0)
    assert parse_color("#1f77b4") == (0x1F, 0x77, 0xB4)
    assert parse_color("1f77b4") == (0x1F, 0x77, 0xB4)
    with pytest.raises(ValueError):
        parse_color("not-a-color")


def test_match_stroke_color(tmp_path):
    png = tmp_path / "fig.png"
    make_plot(png)  # black curve
    img = cv2.imread(str(png))
    frame = find_frame(sobel_magnitude(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)))
    roi = plot_roi(img.shape[:2], frame)
    bgr = match_stroke_color(img, roi, "black")
    assert sum(bgr) < 100  # near-black, not the light grey grid or white background


def test_cli_end_to_end(tmp_path):
    png = tmp_path / "fig.png"
    make_plot(png)  # black curve on a white background with a light grey grid
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "colors", str(png), "--n", "2"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    lines = r.stdout.strip().splitlines()
    assert 1 <= len(lines) <= 2
    assert any("black" in line and "#" in line for line in lines)
    assert not (tmp_path / "curve.csv").exists()
