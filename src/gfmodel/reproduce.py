"""Reproduce the numbers and curves that Dorst (2026) reports for this model.

Each row compares one of our numbers with one number from the paper.  "Paper value" is either
printed in the paper's text (source "text") or read by eye from a figure image (source "figure",
accuracy about +-0.01, so the tolerance is wider).  The tolerance is chosen before looking at the
result: 0.01 for a number printed with two decimals or as a whole percent (rounding is up to 0.005,
and the paper's own simulation has sampling noise), 0.02 for numbers read from a figure or
computed from sequences we do not have.

Our numbers come from ``vectorized.py`` (numpy, independent of the pure-Python reference), with
the Monte Carlo standard error reported.  Run ``uv run python scripts/reproduce_paper.py``.
"""

from __future__ import annotations

import numpy as np

from . import vectorized as V
from .model import build_space, p_continue

ALL8 = [[(v >> t) & 1 for t in range(8)] for v in range(256)]
_SWITCHES = np.array([sum(q[t] != q[t - 1] for t in range(1, 8)) for q in ALL8])
SW_MASKS = [_SWITCHES <= 1, (_SWITCHES >= 3) & (_SWITCHES <= 4), _SWITCHES >= 6]

# Fig. 6 (top middle), 25- and 40-outcome learners, streak lengths 1..7, read by eye from the
# published figure (https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.70171, Fig. 6).
FIG6_BY_EYE = {
    25: [0.483, 0.470, 0.477, 0.520, 0.582, 0.628, 0.670],
    40: [0.488, 0.477, 0.478, 0.497, 0.532, 0.557, 0.580],
}


def expected_switches(chain, n: int) -> float:
    """Expected number of switches in a sequence of n outcomes drawn from ``chain``."""
    maxk = n + 1
    dist = np.zeros(maxk + 1)
    dist[1] = 1.0
    pc = np.array([p_continue(chain, max(k, 1)) for k in range(maxk + 1)])
    total = 0.0
    for _ in range(2, n + 1):
        sw = float((dist * (1.0 - pc)).sum())
        total += sw
        nxt = np.zeros(maxk + 1)
        nxt[2:] = dist[1:-1] * pc[1:-1]
        nxt[1] = sw
        dist = nxt
    return total


def _mc(fn, chunks: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Mean and standard error of a vector statistic over independent chunks of simulated learners."""
    vals = np.array([fn(seed + 1000 * i) for i in range(chunks)])
    se = vals.std(axis=0, ddof=1) / np.sqrt(chunks) if chunks > 1 else np.zeros(vals.shape[1])
    return vals.mean(axis=0), se


def _row(rid, source, where, quantity, paper, tol, ours, se, note=""):
    ours = float(ours)
    return {
        "id": rid,
        "source": source,
        "where": where,
        "quantity": quantity,
        "paper": paper,
        "tolerance": tol,
        "ours": round(ours, 4),
        "mc_se": round(float(se), 4),
        "difference": round(ours - paper, 4),
        "within_tolerance": abs(ours - paper) <= tol,
        "note": note,
    }


def run(quick: bool = False, seed: int = 20261016) -> list[dict]:
    """Compute all comparison rows.  ``quick`` uses fewer simulated learners (for the tests)."""
    big = 20000 if quick else 100000
    chunks = 2 if quick else 5
    rows: list[dict] = []
    space = build_space()
    classes = ["switchy", "steady", "sticky"]

    # --- Section 4: mean posteriors after 20 outcomes (exact) and 50 outcomes (Monte Carlo) ---
    exact20 = V.class_means(space, V.exact_loglik(space, 20))
    paper20 = {"switchy": 0.28, "steady": 0.57, "sticky": 0.15}
    for c in classes:
        rows.append(
            _row(
                f"R1-{c}",
                "text",
                "Section 4, Fig. 4 top right",
                f"mean posterior in {c.capitalize()} after 20 outcomes (exact sum over 2^20 sequences)",
                paper20[c],
                0.01,
                exact20[c],
                0.0,
            )
        )

    def post50(sd):
        ll = V.simulate_loglik(space, [50], big, sd)[50]
        m = V.class_means(space, ll)
        return np.array([m[c] for c in classes])

    mean50, se50 = _mc(post50, chunks, seed)
    paper50 = {"switchy": 0.13, "steady": 0.84, "sticky": 0.03}
    for i, c in enumerate(classes):
        rows.append(
            _row(
                f"R2-{c}",
                "text",
                "Section 4, Fig. 4 top right",
                f"mean posterior in {c.capitalize()} after 50 outcomes",
                paper50[c],
                0.01,
                mean50[i],
                se50[i],
            )
        )

    # --- Section 4, Fig. 4 bottom right: unsure about the speed (21 hypotheses) ---
    mix = build_space(p_steady=1 / 21, speed_mixture=True)

    def mixture_stat(sd):
        ll = V.simulate_loglik(mix, [1, 250, 400], big // 4, sd)
        out = []
        for n in (1, 250, 400):
            m = V.class_means(mix, ll[n])
            out.append(m["steady"] if n == 1 else m["switchy"])
        return np.array(out)

    mmean, mse = _mc(mixture_stat, chunks, seed + 1)
    rows.append(
        _row(
            "R3-start",
            "figure",
            "Fig. 4 bottom right (by eye)",
            "mean posterior in Steady at the start, 21 equally likely chains",
            0.05,
            0.01,
            mmean[0],
            mse[0],
            "1/21 = 0.048",
        )
    )
    rows.append(
        _row(
            "R3-250",
            "text",
            "Section 4 (p. 13)",
            "mean posterior of all Switchy chains after 250 outcomes (speeds 1-10)",
            0.17,
            0.01,
            mmean[1],
            mse[1],
            "paper: 'around 17%'",
        )
    )
    rows.append(
        _row(
            "R3-400",
            "text",
            "Section 4 (p. 13)",
            "mean posterior of all Switchy chains after 400 outcomes (speeds 1-10)",
            0.08,
            0.01,
            mmean[2],
            mse[2],
            "paper: 'still 8%'",
        )
    )

    # --- Section 5.1 and Fig. 6: 25- and 40-outcome learners shown a streak of length s ---
    def streak_stat(sd):
        ll = V.simulate_loglik(space, [25, 40], big // 4, sd)
        return np.concatenate([V.pcont_by_streak(space, ll[n], "streak", 8)[:7] for n in (25, 40)])

    smean, sse = _mc(streak_stat, chunks, seed + 2)
    ours40 = smean[7:]
    se40 = sse[7:]
    for s, paper in ((1, 0.485), (3, 0.475), (6, 0.55)):
        rows.append(
            _row(
                f"R4-s{s}",
                "text",
                "Section 5.1 (p. 17)",
                f"40-outcome learners: mean probability that a streak of {s} continues",
                paper,
                0.01,
                ours40[s - 1],
                se40[s - 1],
                "paper: 48.5% at 1, 47.5% at 3, 55% at 6",
            )
        )
    for n_idx, n in enumerate((25, 40)):
        block = smean[7 * n_idx : 7 * n_idx + 7]
        block_se = sse[7 * n_idx : 7 * n_idx + 7]
        for s in range(1, 8):
            rows.append(
                _row(
                    f"R5-n{n}-s{s}",
                    "figure",
                    "Fig. 6 top middle (by eye)",
                    f"{n}-outcome learners: mean probability that a streak of {s} continues",
                    FIG6_BY_EYE[n][s - 1],
                    0.02,
                    block[s - 1],
                    block_se[s - 1],
                )
            )

    # --- Section 5.5: IID 8-outcome sequences and 40-outcome learners ---
    def iid_stat(sd):
        ll = V.simulate_loglik(space, [40], big // 20, sd)[40]
        p = V.pcont_by_streak(space, ll, "iid8", 8)
        w = np.array([128, 64, 32, 16, 8, 4, 2, 2]) / 256.0
        return np.array([float((np.array(p) * w).sum())])

    imean, ise = _mc(iid_stat, chunks, seed + 3)
    rows.append(
        _row(
            "R6",
            "text",
            "Section 5.5 (p. 21) and Section 4",
            "40-outcome learners shown IID 8-outcome sequences: overall mean probability of a continuation",
            0.484,
            0.01,
            imean[0],
            ise[0],
            "paper: mean 48.4% (and 'switch' 51.6%)",
        )
    )

    # --- Section 4: expected switches in 11-outcome sequences drawn from the learner's posterior ---
    e_sw = np.array([expected_switches(c, 11) for c in space.chains])

    def switches_stat(sd):
        ll = V.simulate_loglik(space, [40], big // 4, sd)[40]
        return np.array([float((V.posteriors(space, ll) @ e_sw).mean())])

    wmean, wse = _mc(switches_stat, chunks, seed + 4)
    rows.append(
        _row(
            "R7",
            "text",
            "Section 4 (p. 14)",
            "40-outcome learners: mean number of switches in an 11-outcome sequence drawn from their posterior",
            5.13,
            0.02,
            wmean[0],
            wse[0],
            "paper: 5.13, 95% CI [5.124, 5.131]; Steady gives exactly 5.00",
        )
    )

    # --- Section 5.3: sequence-dependence (all 8-outcome sequences, grouped by number of switches) ---
    def seqdep_stat(sd):
        ll = V.simulate_loglik(space, [40], big // 20, sd)[40]
        per_seq = V.pcont_per_sequence(space, ll, ALL8)
        return np.array([float(per_seq[mask].mean()) for mask in SW_MASKS])

    dmean, dse = _mc(seqdep_stat, chunks, seed + 6)
    for i, (label, paper) in enumerate(
        (("0-1 switches", 0.555), ("3-4 switches", 0.485), ("6-7 switches", 0.466))
    ):
        rows.append(
            _row(
                f"R8-{i}",
                "text",
                "Section 5.3 (p. 20)",
                f"40-outcome learners shown an 8-outcome sequence with {label}: mean P(continue)",
                paper,
                0.02,
                dmean[i],
                dse[i],
                "paper used the specific sequences of Bloomfield & Hales, which we do not have; "
                "we average over all 8-outcome sequences with that many switches",
            )
        )

    # --- Section 4: Steady after 100 and 150 outcomes (informational) ---
    def late_stat(sd):
        ll = V.simulate_loglik(space, [150], big // 10, sd)[150]
        return np.array([V.class_means(space, ll)["steady"]])

    lmean, lse = _mc(late_stat, chunks, seed + 5)
    rows.append(
        _row(
            "I1",
            "text",
            "Section 4 (p. 14)",
            "mean posterior in Steady after 150 outcomes (informational)",
            0.95,
            0.05,
            lmean[0],
            lse[0],
            "paper text: 'already around 95%'; its Fig. 4 shows about 0.98 here",
        )
    )
    return rows


def write_csv(rows: list[dict], path) -> None:
    import csv

    fields = [
        "id",
        "source",
        "where",
        "quantity",
        "paper",
        "tolerance",
        "ours",
        "mc_se",
        "difference",
        "within_tolerance",
        "note",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
