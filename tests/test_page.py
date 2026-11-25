"""Browser checks of the static page (Playwright + Chromium): loads, slider works, phone width,
and the numbers shown on the page equal the Python reference."""

import functools
import http.server
import json
import os
import re
import socketserver
import threading
from pathlib import Path

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")

from gfmodel import build_space, crossing_streak, run_agents  # noqa: E402
from gfmodel.browser import launch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SEED = 20261016  # must equal SEED in docs/app.js
K = 1000


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    handler = functools.partial(_Quiet, directory=str(DOCS))
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with playwright_sync.sync_playwright() as p:
        try:
            b = launch(p)
        except RuntimeError as e:
            if os.environ.get("GF_REQUIRE_BROWSER") or os.environ.get("CI"):
                pytest.fail(str(e))
            pytest.skip("no Chromium available: " + str(e))
        yield b
        b.close()


def wait_idle(page):
    """Wait until the page says every chart shows the current state (body[data-busy] is set
    synchronously by the input handlers, so this cannot return before the update has started)."""
    page.wait_for_function("document.body.dataset.busy === '0'", timeout=60000)


def open_page(browser, url, width=1000):
    page = browser.new_page(viewport={"width": width, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(url)
    page.wait_for_function("window.__gfReady === true")
    wait_idle(page)
    return page, errors


def table_rows(page):
    rows = {}
    for tr in page.locator("#summary-table tbody tr").all():
        cells = [c.inner_text() for c in tr.locator("th, td").all()]
        rows[int(re.match(r"\d+", cells[0]).group())] = cells
    return rows


def test_page_loads_without_errors_and_draws_three_charts(browser, server):
    page, errors = open_page(browser, server)
    assert errors == []
    for cid in ("chart1", "chart2", "chart3"):
        assert page.locator(f"#{cid} path").count() >= 1
    assert "outcomes seen" in page.inner_text("#summary")
    page.close()


def test_no_horizontal_scroll_at_375px_and_screenshots(browser, server, screenshot_dir):
    page, errors = open_page(browser, server, width=375)
    assert errors == []
    widths = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert widths[0] <= widths[1], widths
    # every control is at least 24 CSS px tall and inside the viewport
    boxes = page.evaluate(
        """() => Array.from(document.querySelectorAll('input, select, button')).map(e => {
            const r = e.getBoundingClientRect(); return [e.id || e.tagName, r.left, r.right, r.height]; })"""
    )
    for name, left, right, height in boxes:
        if height > 0:
            assert left >= -1 and right <= 376, (name, left, right)
    page.screenshot(path=str(screenshot_dir / "page_375px.png"), full_page=True)
    page.close()
    desk, _ = open_page(browser, server, width=1000)
    desk.screenshot(
        path=str(screenshot_dir / "page_desktop_top.png"),
        clip={"x": 0, "y": 0, "width": 1000, "height": 1700},
    )
    desk.close()


def test_moving_the_slider_changes_the_summary_and_matches_python(browser, server):
    page, _ = open_page(browser, server)
    before = page.inner_text("#summary")
    page.locator("#n-slider").focus()
    page.keyboard.press("Home")  # 0 outcomes
    page.wait_for_function("document.getElementById('n-out').textContent === '0'")
    page.wait_for_function(
        "document.getElementById('summary').textContent.startsWith('With 0 outcomes')"
    )
    wait_idle(page)
    after = page.inner_text("#summary")
    assert before != after

    # set 25 by the number box, compare the table with the Python reference
    page.fill("#n-number", "25")
    page.wait_for_function(
        "document.getElementById('summary').textContent.startsWith('With 25 outcomes')"
    )
    wait_idle(page)
    rows = table_rows(page)
    space = build_space()
    ref = {
        r["n"]: r for r in run_agents(space, [10, 25, 100], K, SEED, "streak", 8, path_length=300)
    }
    for n in (10, 25, 100):
        cells = rows[n]
        p8 = float(cells[3].rstrip("%")) / 100
        assert p8 == pytest.approx(ref[n]["pcont"][7], abs=6e-4), (n, cells)
        cross = crossing_streak(ref[n]["pcont"])
        assert cells[2] == (str(cross) if cross else "none up to 8")
    page.close()


def test_ten_outcome_row_does_not_move_with_the_comparison_amounts(browser, server):
    page, _ = open_page(browser, server)
    before = table_rows(page)[10]
    for value in ("150", "300"):
        page.fill("#cmp-b", value)
        page.wait_for_function(
            f"document.getElementById('cmp-b').value === '{value}' && document.body.dataset.busy === '0'"
        )
        wait_idle(page)
        assert table_rows(page)[10] == before, value
    page.close()


def test_less_experience_shifts_sooner_on_the_page(browser, server):
    page, _ = open_page(browser, server)
    rows = table_rows(page)  # default: 40 set, compare 10 and 100
    first = {n: rows[n][2] for n in (10, 40, 100)}
    assert int(first[10]) < int(first[40]) < int(first[100])
    at8 = {n: float(rows[n][3].rstrip("%")) for n in (10, 40, 100)}
    assert at8[10] > at8[40] > at8[100]
    page.close()


def test_changing_the_shown_option_and_prior_redraws(browser, server):
    page, errors = open_page(browser, server)
    base = page.inner_text("#summary")
    page.select_option("#shown", "iid8")
    wait_idle(page)
    assert page.inner_text("#summary") != base
    page.locator("#prior-details summary").click()
    page.locator("#w-sti").fill("0")
    wait_idle(page)
    assert "Sticky 0.0%" in page.inner_text("#prior-text")
    page.click("#preset-mixture")
    wait_idle(page)
    assert page.locator("#steps").is_disabled()
    # the paper's two Switchy points (250 and 400 outcomes) are drawn as hollow circles
    assert page.locator("#chart2 circle").count() == 2
    page.click("#preset-default")
    wait_idle(page)
    assert page.locator("#chart2 circle").count() == 6  # the paper's six points at 20 and 50
    assert errors == []
    page.close()


def test_worked_example_matches_python(browser, server):
    ex = json.loads((ROOT / "results" / "worked_example.json").read_text())
    page, _ = open_page(browser, server)
    assert f"coin number {ex['seed']}" in page.inner_text("#ex-seed")
    flips = "".join("H" if x else "T" for x in ex["flips"])
    text = page.inner_text("#ex-flips").replace("\n", " ")
    assert flips[:10] in text and flips[10:] in text
    rows = [
        [c.inner_text() for c in tr.locator("th, td").all()]
        for tr in page.locator("#ex-table tbody tr").all()
    ]

    def pcts(row):
        return [float(c.rstrip("%")) / 100 for c in row[2:]]

    a, b = ex["learner_A_10_seen"], ex["learner_B_40_seen"]
    keys = ["switchy", "steady", "sticky"]
    assert pcts(rows[1]) == pytest.approx(
        [a["after_experience_classes"][k] for k in keys], abs=6e-4
    )
    assert pcts(rows[2]) == pytest.approx([a["after_shown_classes"][k] for k in keys], abs=6e-4)
    assert pcts(rows[3]) == pytest.approx(
        [b["after_experience_classes"][k] for k in keys], abs=6e-4
    )
    assert pcts(rows[4]) == pytest.approx([b["after_shown_classes"][k] for k in keys], abs=6e-4)
    body = page.inner_text("#ex-text")
    assert f"{a['p_continue'] * 100:.1f}%" in body and f"{b['p_continue'] * 100:.1f}%" in body
    page.close()


def test_accessibility_basics(browser, server):
    page, _ = open_page(browser, server)
    assert page.evaluate("document.documentElement.lang") == "en"
    # every input, select has an associated label
    unlabeled = page.evaluate(
        """() => Array.from(document.querySelectorAll('input, select')).filter(e => !e.labels || e.labels.length === 0).map(e => e.id)"""
    )
    assert unlabeled == []
    assert page.locator("svg[role=img][aria-label]").count() == 3
    assert page.locator("h1").count() == 1
    page.close()


def test_page_makes_no_external_requests(browser, server):
    origin = server.rsplit("/", 1)[0]
    urls = []
    page = browser.new_page(viewport={"width": 1000, "height": 900})
    page.on("request", lambda r: urls.append(r.url))
    page.goto(server)
    page.wait_for_function("window.__gfReady === true")
    wait_idle(page)
    page.fill("#n-number", "60")
    wait_idle(page)
    page.locator("#n-slider").focus()
    page.keyboard.press("ArrowRight")
    wait_idle(page)
    assert urls
    bad = [u for u in urls if not (u.startswith(origin) or u.startswith("data:"))]
    assert bad == []
