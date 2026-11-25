"""Read the page's own summary table at 10, 40 and 100 outcomes (headless Chromium on a local
server of docs/) and compare with results/experience_curves.csv. Writes results/live_page_numbers.csv.

    uv run python scripts/live_page_numbers.py
"""

import csv
import functools
import http.server
import re
import socketserver
import sys
import threading
from pathlib import Path

from playwright import sync_api

from gfmodel.browser import launch

ROOT = Path(__file__).resolve().parents[1]
SRC = "page_settings_1000_learners_seed_20261016"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> int:
    srv = socketserver.TCPServer(
        ("127.0.0.1", 0), functools.partial(_Quiet, directory=str(ROOT / "docs"))
    )
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    csv_rows = list(csv.DictReader((ROOT / "results/experience_curves.csv").open()))
    expect = {
        int(r["n_seen"]): float(r["mean_p_continue"])
        for r in csv_rows
        if r["source"] == SRC and r["streak_length"] == "8"
    }
    out, bad = [], 0
    with sync_api.sync_playwright() as p:
        b = launch(p)
        page = b.new_page(viewport={"width": 1000, "height": 900})
        page.goto(f"http://127.0.0.1:{srv.server_address[1]}/index.html")
        page.wait_for_function("window.__gfReady === true && document.body.dataset.busy === '0'")
        for n in (10, 40, 100):  # default page: slider 40, comparison amounts 10 and 100
            for tr in page.locator("#summary-table tbody tr").all():
                c = [x.inner_text() for x in tr.locator("th, td").all()]
                if int(re.match(r"\d+", c[0]).group()) == n:
                    p8 = float(c[3].rstrip("%")) / 100
                    ok = abs(p8 - expect[n]) < 6e-4
                    bad += not ok
                    out.append((n, c[2], c[3], expect[n], "ok" if ok else "DIFF"))
        b.close()
    srv.shutdown()
    with (ROOT / "results/live_page_numbers.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "n_seen",
                "first_streak_expecting_continuation",
                "page_p_after_8",
                "csv_p_after_8",
                "check",
            ]
        )
        w.writerows(out)
    for r in out:
        print(*r)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
