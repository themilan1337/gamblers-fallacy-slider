import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def pytest_terminal_summary(terminalreporter):
    skipped = terminalreporter.stats.get("skipped", [])
    n = 0
    for rep in skipped:
        longrepr = rep.longrepr
        reason = longrepr[2] if isinstance(longrepr, tuple) else str(longrepr)
        if reason.removeprefix("Skipped: ").startswith("no Chromium"):
            n += 1
    if n:
        terminalreporter.write_line(
            f"WARNING: {n} browser tests were skipped (no Chromium); the page was NOT tested. "
            "Run `uv run playwright install chromium` or set GF_CHROMIUM.",
            red=True,
        )


@pytest.fixture(scope="session")
def screenshot_dir(tmp_path_factory):
    """Temporary folder, unless GF_SAVE_SCREENSHOTS=1: then the tracked results/ folder."""
    if os.environ.get("GF_SAVE_SCREENSHOTS") == "1":
        d = ROOT / "results"
        d.mkdir(exist_ok=True)
        return d
    return tmp_path_factory.mktemp("shots")
