import re
import subprocess
import sys

import pytest
from synthetic import make_plot

from vector_trace.cli import _cal
from vector_trace.wizard import build_command, format_cal_pair, parse_typed_value


def test_format_cal_pair_roundtrips_through_cli_parser():
    formatted = format_cal_pair(193, 12.5)
    assert formatted == "193:12.5"
    assert _cal([formatted]) == [(193.0, 12.5)]


def test_format_cal_pair_no_trailing_noise():
    assert format_cal_pair(193, 0.0) == "193:0"
    assert format_cal_pair(193.0, 12.0) == "193:12"


def test_build_command_seed():
    cmd = build_command(
        "fig.png", [(193, 0), (1052, 12)], [(653, 0), (88, 140)],
        xlog=False, ylog=False, seed=(908, 335), output="curve.csv",
    )
    assert cmd == (
        "vector-trace extract fig.png --xcal 193:0 1052:12 --ycal 653:0 88:140 "
        "--seed 908,335 -o curve.csv"
    )


def test_build_command_color():
    cmd = build_command(
        "fig.png", [(193, 0), (1052, 12)], [(653, 0), (88, 140)],
        xlog=False, ylog=False, color="blue", output="blue.csv",
    )
    assert "--color blue" in cmd
    assert "--seed" not in cmd
    assert cmd.endswith("-o blue.csv")


def test_build_command_xlog_ylog_omitted_when_false():
    cmd = build_command("fig.png", [(1, 1), (2, 2)], [(1, 1), (2, 2)], xlog=False, ylog=False, seed=(0, 0))
    assert "--xlog" not in cmd and "--ylog" not in cmd


def test_build_command_xlog_ylog_included_when_true():
    cmd = build_command("fig.png", [(1, 1), (2, 2)], [(1, 1), (2, 2)], xlog=True, ylog=True, seed=(0, 0))
    assert "--xlog" in cmd and "--ylog" in cmd


def test_build_command_quotes_image_with_spaces():
    cmd = build_command("my fig.png", [(1, 1), (2, 2)], [(1, 1), (2, 2)], xlog=False, ylog=False, seed=(0, 0))
    assert "'my fig.png'" in cmd


def test_parse_typed_value_rejects_non_numeric():
    with pytest.raises(ValueError):
        parse_typed_value("abc", log=False)


def test_parse_typed_value_rejects_nonpositive_for_log():
    for bad in ("0", "-5", "nan", "inf"):
        with pytest.raises(ValueError):
            parse_typed_value(bad, log=True)
    assert parse_typed_value("5", log=True) == 5.0


def test_guide_fails_with_clear_gui_error(tmp_path):
    png = tmp_path / "fig.png"
    make_plot(png)
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "guide", str(png)],
        capture_output=True,
        text=True,
    )
    # opencv-python-headless (installed for this project) has no GUI support,
    # and this must fail before any terminal prompt -- no stdin needed.
    assert r.returncode == 1
    assert "opencv-python" in r.stderr
    assert list(tmp_path.iterdir()) == [png]


def test_guide_bad_image_rejected(tmp_path):
    missing = tmp_path / "nope.png"
    r = subprocess.run(
        [sys.executable, "-m", "vector_trace", "guide", str(missing)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
    assert "cannot read image" in r.stderr
    assert list(tmp_path.iterdir()) == []


def test_guide_help_lists_output_flag():
    r = subprocess.run([sys.executable, "-m", "vector_trace", "guide", "--help"], capture_output=True, text=True)
    assert "--output" in r.stdout


def test_man_documents_guide_options():
    help_text = subprocess.run(
        [sys.executable, "-m", "vector_trace", "guide", "--help"], capture_output=True, text=True
    ).stdout
    man = subprocess.run([sys.executable, "-m", "vector_trace", "--man"], capture_output=True, text=True).stdout
    for opt in set(re.findall(r"--[a-z][a-z-]*", help_text)):
        assert opt in man, f"{opt} is in guide --help but missing from --man"
