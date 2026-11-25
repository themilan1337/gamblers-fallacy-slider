"""Run the JavaScript port (docs/model.js) and the Python reference on the same cases and compare.

Used by tests/test_crosscheck_js.py (pass/fail at 1e-9) and scripts/crosscheck_report.py (writes the
largest observed difference to results/crosscheck_report.json).
"""

from __future__ import annotations

import itertools
import json
import subprocess
from pathlib import Path

from .experience import run_agents, steady_sequence
from .model import Chain, build_space, log_likelihood, predict_after

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tests" / "js_runner.cjs"


def run_node(cases: list[dict]) -> list:
    proc = subprocess.run(
        ["node", str(RUNNER)],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
        timeout=600,
    )
    return json.loads(proc.stdout)


def space_kwargs_to_py(d: dict) -> dict:
    return {
        "p_steady": d.get("pSteady", 1 / 3),
        "switchy_share": d.get("switchyShare", 0.5),
        "steps": d.get("steps", 4),
        "degree": d.get("degree", 0.9),
        "speed_mixture": d.get("speedMixture", False),
    }


def agent_cases() -> list[dict]:
    """The parameter grid: chain steps x maximum shift x prior, both display modes, speed mixtures."""
    cases = []
    steps_degree = [(4, 0.9), (1, 0.9), (2, 0.7), (7, 0.6), (10, 0.95)]
    priors = [(1 / 3, 0.5), (0.05, 0.5), (0.6, 0.3), (0.0, 0.8), (0.2, 1.0)]
    for i, ((steps, degree), (ps, share)) in enumerate(itertools.product(steps_degree, priors)):
        cases.append(
            {
                "kind": "agents",
                "space": {"pSteady": ps, "switchyShare": share, "steps": steps, "degree": degree},
                "ns": [0, 1, 5, 12, 40, 120],
                "k": 60,
                "seed": 1000 + i,
                "shown_mode": "iid8" if i % 2 == 0 else "streak",
                "shown_length": 8,
            }
        )
    for i, (ps, mode) in enumerate([(1 / 21, "streak"), (1 / 3, "iid8"), (0.5, "streak")]):
        cases.append(
            {
                "kind": "agents",
                "space": {"pSteady": ps, "speedMixture": True, "degree": 0.9},
                "ns": [0, 10, 100, 250],
                "k": 25,
                "seed": 77 + i,
                "shown_mode": mode,
                "shown_length": 8,
            }
        )
    base = {"kind": "agents", "space": {}, "k": 40}
    cases.append({**base, "ns": [3, 30], "seed": 5, "shown_mode": "iid8", "shown_length": 6})
    cases.append({**base, "ns": [3, 30, 300], "seed": 6, "shown_mode": None, "shown_length": 8})
    return cases


def learner_cases() -> list[dict]:
    cases = []
    for seed in (1, 2, 3, 2026):
        cases.append({"kind": "sequence", "seed": seed, "n": 57})
    exp = steady_sequence(4, 25)
    spaces = (
        {},
        {"pSteady": 0.1, "switchyShare": 0.8, "steps": 3, "degree": 0.75},
        {"speedMixture": True},
    )
    for shown in ([1, 1, 1, 1], [1, 0, 1, 0, 1], [0] * 7, [1, 0, 0, 1, 1, 1, 1, 1]):
        for space in spaces:
            cases.append({"kind": "learner", "space": space, "experience": exp, "shown": shown})
    chains = [(-1, 4, 0.9), (0, 4, 0.9), (1, 4, 0.9), (-1, 2, 0.7), (1, 9, 0.55)]
    for seq in (exp, [1], [], [0, 0, 0, 0, 0, 0, 0, 0, 1]):
        cases.append({"kind": "loglik", "chains": chains, "seq": seq})
    return cases


def python_result(case: dict):
    """The Python reference's answer to one case, in the same shape as js_runner.cjs returns."""
    if case["kind"] == "agents":
        from .experience import crossing_streak

        space = build_space(**space_kwargs_to_py(case["space"]))
        rows = run_agents(
            space,
            case["ns"],
            case["k"],
            case["seed"],
            case["shown_mode"],
            case["shown_length"],
            path_length=case.get("path_length"),
        )
        return {"rows": rows, "crossings": [crossing_streak(r["pcont"]) for r in rows]}
    if case["kind"] == "sequence":
        return steady_sequence(case["seed"], case["n"])
    if case["kind"] == "loglik":
        return [log_likelihood(Chain(*c), case["seq"]) for c in case["chains"]]
    space = build_space(**space_kwargs_to_py(case["space"]))
    return predict_after(space, case["experience"], case["shown"])


def compare(a, b, path: str = "") -> tuple[float, int]:
    """Largest absolute difference and the count of numbers compared; raises on structure mismatch."""
    if isinstance(a, dict):
        if not isinstance(b, dict) or set(a) != set(b):
            raise AssertionError(f"structure differs at {path}")
        worst, count = 0.0, 0
        for k in a:
            w, c = compare(a[k], b[k], f"{path}.{k}")
            worst, count = max(worst, w), count + c
        return worst, count
    if isinstance(a, list | tuple):
        if len(a) != len(b):
            raise AssertionError(f"length differs at {path}")
        worst, count = 0.0, 0
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            w, c = compare(x, y, f"{path}[{i}]")
            worst, count = max(worst, w), count + c
        return worst, count
    if a is None or b is None:
        if not (a is None and b is None):
            raise AssertionError(f"None mismatch at {path}")
        return 0.0, 0
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b), 1
    if a != b:
        raise AssertionError(f"values differ at {path}: {a!r} vs {b!r}")
    return 0.0, 1


def run_all() -> dict:
    cases = agent_cases() + learner_cases()
    js = run_node(cases)
    worst, count = 0.0, 0
    for case, got in zip(cases, js, strict=True):
        w, c = compare(python_result(case), got, case["kind"])
        worst, count = max(worst, w), count + c
    return {"cases": len(cases), "numbers_compared": count, "max_abs_difference": worst}
