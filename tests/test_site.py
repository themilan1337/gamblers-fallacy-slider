"""Static-site checks (no browser): relative paths, no CDN."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HTML = (DOCS / "index.html").read_text(encoding="utf-8")
ALLOWED = ("https://doi.org/", "https://osf.io/", "https://www.kevindorst.com/", "data:")


def _urls():
    return re.findall(r'(?:src|href)="([^"]*)"', HTML)


def test_urls_are_relative_or_allowed_hosts():
    for u in _urls():
        local = not re.match(r"^[a-z]+:|^//", u)
        assert local or u.startswith(ALLOWED), u
    assert "//cdn" not in HTML
    assert "http://" not in HTML


def test_no_absolute_paths():
    assert not [u for u in _urls() if u.startswith("/")]


def test_local_files_exist():
    for u in _urls():
        if re.match(r"^[a-z]+:", u) or u.startswith("#"):
            continue
        assert (DOCS / u.split("#")[0]).is_file(), u


def test_nojekyll_exists():
    assert (DOCS / ".nojekyll").is_file()


def test_noscript_says_javascript_is_needed():
    m = re.search(r"<noscript>(.*?)</noscript>", HTML, re.S)
    assert m and "JavaScript" in m.group(1)
