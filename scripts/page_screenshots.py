"""Screenshots of docs/ at 375 px and 1280 px, plus an optional keyboard pass.

Serves docs/ on a free local port, opens it headless (Chromium or Chrome found by
gfmodel.browser, so it also works on a Mac), checks that the page does not scroll
sideways and has no console error, and saves full-page PNGs to results/.

    uv run python scripts/page_screenshots.py --keyboard

Exit code 1 on a horizontal scroll, a console error, a missing skip link or a focused
control without an outline. Nothing is uploaded.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

from gfmodel.browser import launch

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RESULTS = ROOT / "results"
VIEWPORTS = ((375, 800, "page_375px.png"), (1280, 900, "page_desktop_top.png"))
FOCUS_STOPS = 12


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _open(browser, url: str, width: int, height: int):
    page = browser.new_page(viewport={"width": width, "height": height})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(url)
    page.wait_for_function("window.__gfReady === true", timeout=60000)
    page.wait_for_function("document.body.dataset.busy === '0'", timeout=60000)
    return page, errors


def shoot(browser, url: str, out_dir: Path) -> bool:
    ok = True
    for width, height, name in VIEWPORTS:
        page, errors = _open(browser, url, width, height)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        inner = page.evaluate("window.innerWidth")
        page.screenshot(path=str(out_dir / name), full_page=True)
        page.close()
        print(
            f"{width} px: scrollWidth {scroll} <= innerWidth {inner}, {len(errors)} console errors"
        )
        if scroll > inner or errors:
            ok = False
            for e in errors:
                print("  error:", e)
    return ok


def keyboard(browser, url: str) -> bool:
    page, _ = _open(browser, url, 1280, 900)
    stops = []
    for _ in range(FOCUS_STOPS):
        page.keyboard.press("Tab")
        stops.append(
            page.evaluate(
                """() => {
                  const e = document.activeElement;
                  const s = getComputedStyle(e);
                  return {id: e.id || e.className || e.tagName,
                          cls: e.className, outline: s.outlineStyle,
                          shadow: s.boxShadow};
                }"""
            )
        )
    page.close()
    bad = [s for s in stops if s["outline"] == "none"]
    skip_first = "skip" in stops[0]["cls"]
    print("focus order:", ", ".join(str(s["id"]) for s in stops))
    print(
        f"keyboard: {'skip link first' if skip_first else 'skip link NOT first'}, "
        f"{len(stops)} focus stops, {len(bad)} without an outline"
    )
    return skip_first and not bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyboard", action="store_true", help="also run the Tab-key pass")
    ap.add_argument("--out", type=Path, default=RESULTS, help="folder for the PNGs")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(_Quiet, directory=str(DOCS))
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    ok = True
    try:
        with sync_playwright() as p:
            browser = launch(p)
            ok = shoot(browser, url, args.out)
            if args.keyboard:
                ok = keyboard(browser, url) and ok
            browser.close()
    except RuntimeError as e:
        print(e)
        return 1
    finally:
        srv.shutdown()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
