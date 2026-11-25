"""Pick the simulated coin for the page's worked example, and write results/worked_example.json.

The example shows two learners (A: first 10 flips, B: all 40) who then both see a miss and 5 hits.
A single pair of learners can differ a lot from the average, so the default coin is the first
seed (1, 2, 3, ...) whose two learners are both close to the average learner of that experience:
their posteriors within 0.08 of the mean posteriors, and their probability of a continuation within
0.05 of the mean (over 4000 simulated learners, bare-streak display, streak of 5).  This is a
presentation choice, stated on the page and in the README; other seeds are one click away.

    uv run python scripts/choose_example_seed.py
"""

import json
from pathlib import Path

from gfmodel import build_space, predict_after, run_agents, steady_sequence

ROOT = Path(__file__).resolve().parents[1]
SHOWN = [0, 1, 1, 1, 1, 1]


def main() -> None:
    space = build_space()
    avg = {r["n"]: r for r in run_agents(space, [10, 40], 4000, 20261016, "streak")}
    chosen = None
    for seed in range(1, 500):
        flips = steady_sequence(seed, 40)
        a = predict_after(space, flips[:10], SHOWN)
        b = predict_after(space, flips, SHOWN)
        ok = True
        for n, r in ((10, a), (40, b)):
            m = avg[n]
            for key in ("switchy", "steady", "sticky"):
                if abs(r["after_experience_classes"][key] - m["class_post"][key]) > 0.08:
                    ok = False
            if abs(r["p_continue"] - m["pcont"][4]) > 0.05:
                ok = False
        if ok:
            chosen = seed
            break
    assert chosen is not None
    flips = steady_sequence(chosen, 40)
    out = {
        "seed": chosen,
        "flips": flips,
        "shown": SHOWN,
        "average_learner": {
            str(n): {"class_post": avg[n]["class_post"], "pcont_streak5": avg[n]["pcont"][4]}
            for n in avg
        },
        "learner_A_10_seen": predict_after(space, flips[:10], SHOWN),
        "learner_B_40_seen": predict_after(space, flips, SHOWN),
    }
    path = ROOT / "results" / "worked_example.json"
    path.write_text(json.dumps(out, indent=2))
    print("chosen seed", chosen)
    print(
        "A p_continue",
        out["learner_A_10_seen"]["p_continue"],
        "B",
        out["learner_B_40_seen"]["p_continue"],
    )
    print("average p_continue (streak 5): N=10", avg[10]["pcont"][4], "N=40", avg[40]["pcont"][4])


if __name__ == "__main__":
    main()
