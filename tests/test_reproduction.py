"""The model reproduces the numbers and curves reported in Dorst (2026).

``gfmodel.reproduce.run`` lists each comparison (source section or figure, the paper's value, a
tolerance fixed in advance, our value).  The full run is ``scripts/reproduce_paper.py``; this test
runs the same list with fewer simulated learners.
"""

import pytest

from gfmodel.model import Chain
from gfmodel.reproduce import expected_switches, run


@pytest.fixture(scope="module")
def rows():
    return run(quick=True)


def test_every_comparison_is_within_its_tolerance(rows):
    bad = [r for r in rows if not r["within_tolerance"]]
    assert not bad, [(r["id"], r["paper"], r["ours"]) for r in bad]
    ids = {r["id"] for r in rows}
    # the figure numbers the page reproduces: Fig. 4 (mean posteriors) and Fig. 6 (streak curves)
    assert {"R1-steady", "R2-steady", "R3-250", "R4-s6", "R5-n25-s7", "R5-n40-s4"} <= ids
    assert len(rows) >= 30


def test_text_numbers_are_matched_to_within_one_percentage_point(rows):
    text_rows = [
        r for r in rows if r["source"] == "text" and r["id"].startswith(("R1", "R2", "R4"))
    ]
    assert text_rows
    for r in text_rows:
        assert abs(r["ours"] - r["paper"]) <= 0.01 + 3 * r["mc_se"], r


def test_expected_switches_of_steady_is_half_of_the_transitions():
    # 11 outcomes have 10 chances to switch; Steady switches with probability 0.5 each time
    assert expected_switches(Chain(0), 11) == pytest.approx(5.0)
    # Switchy switches more than 50%, Sticky less
    assert expected_switches(Chain(-1, 4, 0.9), 11) > 5.0 > expected_switches(Chain(1, 4, 0.9), 11)
