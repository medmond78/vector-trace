import re
import subprocess
import sys


def _run(*args):
    return subprocess.run([sys.executable, "-m", "vector_trace", *args], capture_output=True, text=True)


def test_man_at_both_levels():
    for args in (["--man"], ["extract", "--man"]):
        r = _run(*args)
        assert r.returncode == 0
        for section in ("NAME", "SYNOPSIS", "DESCRIPTION", "OPTIONS", "EXAMPLES", "EXIT STATUS"):
            assert section in r.stdout


def test_man_documents_every_option():
    help_text = _run("extract", "--help").stdout
    man = _run("--man").stdout
    for opt in set(re.findall(r"--[a-z][a-z-]*", help_text)):
        assert opt in man, f"{opt} is in --help but missing from --man"
