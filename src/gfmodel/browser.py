"""Find a Chromium or Chrome binary for the browser tests and the screenshot script.

Order: the file named by GF_CHROMIUM (no fallback if it is set but missing), a Playwright
Chromium cache (Linux or macOS), then Google Chrome on macOS. Roots are injectable for tests.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

ENV_VAR = "GF_CHROMIUM"
INSTALL_HINT = "uv run playwright install chromium"

# Patterns are relative to a root ("/" or the home folder in real use), in priority order.
PATTERNS = (
    "opt/pw-browsers/chromium-*/chrome-linux/chrome",
    ".cache/ms-playwright/chromium-*/chrome-linux/chrome",
    "Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
    "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def default_roots() -> list[Path]:
    return [Path("/"), Path.home()]


def find_chromium(
    env: Mapping[str, str] | None = None, roots: Sequence[Path] | None = None
) -> Path | None:
    env = os.environ if env is None else env
    wanted = env.get(ENV_VAR)
    if wanted:
        p = Path(wanted).expanduser()
        return p if p.is_file() else None
    for pattern in PATTERNS:
        for root in roots if roots is not None else default_roots():
            hits = sorted(p for p in root.glob(pattern) if p.is_file())
            if hits:
                return hits[-1]
    return None


def describe_missing(env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    if env.get(ENV_VAR):
        return (
            f"{ENV_VAR}={env[ENV_VAR]} is not a file. Fix the path or unset {ENV_VAR}; "
            f"or run `{INSTALL_HINT}`."
        )
    return (
        f"No Chromium or Chrome found. Run `{INSTALL_HINT}` once, or set {ENV_VAR}=/path/to/chrome "
        "(on a Mac: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')."
    )


def launch(playwright):
    """Launch headless Chromium: GF_CHROMIUM if set, else Playwright's own, else a found binary.

    Raises RuntimeError with `describe_missing()` when nothing works."""
    args = ["--no-sandbox"]
    env_set = bool(os.environ.get(ENV_VAR))
    if not env_set:
        try:
            return playwright.chromium.launch(args=args)
        except Exception:
            pass
    path = find_chromium()
    if path is None:
        raise RuntimeError(describe_missing())
    return playwright.chromium.launch(executable_path=str(path), args=args)
