"""Cross-check: the JavaScript port (docs/model.js, run with Node) against the Python reference.

Both are run on a grid of parameters and must agree to 1e-9 on every number: posteriors, mean
posteriors, mean probabilities of a continuation, shares above 50%, crossing points, the seeded coin
flips, and single-learner predictions.  (Observed differences are about 1e-13, from the last digit
of Math.log / Math.exp versus the C library.)
"""

import shutil

import pytest

from gfmodel import crosscheck as cc

TOL = 1e-9

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")


def test_parameter_grid_agrees_to_1e_9():
    cases = cc.agent_cases() + cc.learner_cases()
    agent_cases = [c for c in cases if c["kind"] == "agents"]
    assert len(agent_cases) >= 28
    js = cc.run_node(cases)
    assert len(js) == len(cases)
    total = 0
    for case, got in zip(cases, js, strict=True):
        worst, count = cc.compare(cc.python_result(case), got, case["kind"])
        assert worst <= TOL, (case, worst)
        total += count
    assert total > 4000


def test_seeded_coin_flips_are_identical():
    cases = [c for c in cc.learner_cases() if c["kind"] == "sequence"]
    for case, got in zip(cases, cc.run_node(cases), strict=True):
        assert got == cc.python_result(case)


def test_the_comparison_would_catch_a_difference():
    # guard against a vacuous check: a perturbed number must be reported
    worst, _ = cc.compare({"x": [1.0, 2.0]}, {"x": [1.0, 2.0 + 1e-6]})
    assert worst > TOL
    with pytest.raises(AssertionError):
        cc.compare({"x": 1}, {"x": 2})


def _path_length_case(**extra):
    return {
        "kind": "agents",
        "space": {"pSteady": 1 / 3, "switchyShare": 0.5, "steps": 4, "degree": 0.9},
        "ns": [10, 40, 100],
        "k": 100,
        "seed": 20261016,
        "shown_mode": "streak",
        "shown_length": 8,
        **extra,
    }


def test_path_length_agrees_between_python_and_js():
    case = _path_length_case(path_length=300)
    worst, count = cc.compare(cc.python_result(case), cc.run_node([case])[0])
    assert worst <= TOL and count > 50


def test_path_length_changes_the_numbers_so_the_check_is_not_vacuous():
    with_len = cc.python_result(_path_length_case(path_length=300))
    without = cc.python_result(_path_length_case())
    worst, _ = cc.compare(with_len["rows"], without["rows"])
    assert worst > 1e-3
