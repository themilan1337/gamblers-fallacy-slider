"""find_chromium looks for a browser in a fixed order and never falls back when GF_CHROMIUM is set."""

from pathlib import Path

from gfmodel.browser import describe_missing, find_chromium

LINUX = "opt/pw-browsers/chromium-1194/chrome-linux/chrome"
MAC_PW = (
    "Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/"
    "Chromium.app/Contents/MacOS/Chromium"
)
MAC_CHROME = "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _touch(root: Path, rel: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")
    return p


def test_env_variable_wins_when_the_file_exists(tmp_path):
    fake = _touch(tmp_path, "mine/chrome")
    _touch(tmp_path, LINUX)
    assert find_chromium({"GF_CHROMIUM": str(fake)}, [tmp_path]) == fake


def test_env_variable_missing_path_gives_none_and_names_the_variable(tmp_path):
    _touch(tmp_path, LINUX)  # must not be used as a fallback
    env = {"GF_CHROMIUM": str(tmp_path / "nope")}
    assert find_chromium(env, [tmp_path]) is None
    assert "GF_CHROMIUM" in describe_missing(env)


def test_playwright_linux_cache_is_found(tmp_path):
    fake = _touch(tmp_path, LINUX)
    assert find_chromium({}, [tmp_path]) == fake


def test_playwright_mac_cache_is_found(tmp_path):
    fake = _touch(tmp_path, MAC_PW)
    assert find_chromium({}, [tmp_path]) == fake


def test_google_chrome_on_mac_is_found_last(tmp_path):
    chrome = _touch(tmp_path, MAC_CHROME)
    assert find_chromium({}, [tmp_path]) == chrome
    pw = _touch(tmp_path, MAC_PW)
    assert find_chromium({}, [tmp_path]) == pw


def test_nothing_found_returns_none_with_install_hint(tmp_path):
    assert find_chromium({}, [tmp_path]) is None
    assert "uv run playwright install chromium" in describe_missing({})
