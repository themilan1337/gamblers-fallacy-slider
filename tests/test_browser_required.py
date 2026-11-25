"""The browser tests fail (not skip) when GF_REQUIRE_BROWSER=1 and Chromium is missing."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_missing_chromium_fails_when_required():
    env = dict(os.environ, GF_CHROMIUM="/nonexistent/chrome", GF_REQUIRE_BROWSER="1")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "tests/test_page.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode != 0
    assert "GF_CHROMIUM" in r.stdout + r.stderr


def test_missing_chromium_skips_with_warning_when_not_required():
    env = dict(os.environ, GF_CHROMIUM="/nonexistent/chrome")
    env.pop("GF_REQUIRE_BROWSER", None)
    env.pop("CI", None)
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_page.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0
    assert "WARNING" in r.stdout and "NOT tested" in r.stdout
