import subprocess
import sys

from synthetic import make_plot


def test_cli_writes_nothing(tmp_path):
    png = tmp_path / "fig.png"
    make_plot(png)
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "preview", str(png)],
        capture_output=True,
        text=True,
    )
    # opencv-python-headless (installed for this project) has no GUI support,
    # so this must fail with a clear message rather than writing any file.
    assert r.returncode == 1
    assert "opencv-python" in r.stderr
    assert list(tmp_path.iterdir()) == [png]


def test_bad_opacity_rejected_before_gui(tmp_path):
    png = tmp_path / "fig.png"
    make_plot(png)
    for opacity in ("-1", "101"):
        r = subprocess.run(
            [sys.executable, "-m", "vector_trace", "preview", str(png), opacity],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 1
        assert "opacity" in r.stderr
    assert list(tmp_path.iterdir()) == [png]


def test_color_resolved_before_gui(tmp_path):
    png = tmp_path / "fig.png"
    make_plot(png)  # black curve
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "preview", str(png), "--color", "black"],
        capture_output=True,
        text=True,
    )
    # --color is resolved (no error about it) before the no-GUI failure; no listing is printed either.
    assert r.returncode == 1
    assert "opencv-python" in r.stderr
    assert r.stdout == ""
    assert list(tmp_path.iterdir()) == [png]


def test_bad_color_rejected_before_gui(tmp_path):
    png = tmp_path / "fig.png"
    make_plot(png)
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "preview", str(png), "--color", "not-a-color"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
    assert "not-a-color" in r.stderr
    assert list(tmp_path.iterdir()) == [png]


def test_seed_and_color_mutually_exclusive(tmp_path):
    png = tmp_path / "fig.png"
    make_plot(png)
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "preview", str(png), "--seed", "1,1", "--color", "black"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
