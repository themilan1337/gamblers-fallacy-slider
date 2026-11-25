"""Make the committed figures and the CSV of experience curves.

    uv run python scripts/make_figures.py            # about 2-3 minutes
    uv run python scripts/make_figures.py --quick    # fewer simulated learners

Outputs in results/:
  experience_curves.csv            mean probability of a continuation by experience and streak length
  fig_reproduction_fig4.png        mean posteriors versus experience, with the paper's printed numbers
  fig_reproduction_fig6.png        streak curves for 25, 40, 75, 100 outcomes, with the paper's numbers
  fig_experience_effect.png        the new part: streak curves for 10 to 300 outcomes of experience
"""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from gfmodel import build_space, crossing_streak, run_agents  # noqa: E402
from gfmodel import vectorized as V  # noqa: E402
from gfmodel.reproduce import FIG6_BY_EYE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
PAGE_SEED = 20261016  # the page's coin flips (docs/app.js)
PAGE_K = 1000
VIOLET = "#6250d6"


def chunked_means(space, ns, total, chunk, seed, shown="streak"):
    """Large Monte Carlo (numpy): mean P(continue) per streak and class posteriors at each N."""
    sums_p = {n: np.zeros(8) for n in ns}
    sums_c = {n: np.zeros(3) for n in ns}
    done = 0
    i = 0
    while done < total:
        m = min(chunk, total - done)
        ll = V.simulate_loglik(space, ns, m, seed + 7919 * i)
        for n in ns:
            sums_p[n] += np.array(V.pcont_by_streak(space, ll[n], shown, 8)) * m
            cm = V.class_means(space, ll[n])
            sums_c[n] += np.array([cm["switchy"], cm["steady"], cm["sticky"]]) * m
        done += m
        i += 1
    return {n: (sums_p[n] / total, sums_c[n] / total) for n in ns}


def write_curves_csv(path, rows):
    """Write (source, n_seen, streak_length, mean_p_continue) rows with LF line endings."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["source", "n_seen", "streak_length", "mean_p_continue"])
        for source, n, streak, value in rows:
            w.writerow([source, n, streak, round(float(value), 5)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    total = 20000 if args.quick else 200000
    RES.mkdir(exist_ok=True)
    space = build_space()
    ns = [0, 10, 25, 40, 75, 100, 150, 300]
    large = chunked_means(space, ns, total, 25000, 12345)
    page = {r["n"]: r for r in run_agents(space, ns, PAGE_K, PAGE_SEED, "streak", 8)}

    page_src = f"page_settings_{PAGE_K}_learners_seed_{PAGE_SEED}"
    large_src = f"large_run_{total}_learners"
    rows = [(page_src, n, k, page[n]["pcont"][k - 1]) for n in ns for k in range(1, 9)]
    rows += [(large_src, n, k, large[n][0][k - 1]) for n in ns for k in range(1, 9)]
    write_curves_csv(RES / "experience_curves.csv", rows)
    print("N   first streak>50% (large run)   P after 8 in a row   lowest")
    for n in ns:
        p = large[n][0]
        print(
            n,
            crossing_streak(list(p)),
            round(float(p[7]), 4),
            round(float(p.min()), 4),
            "at",
            int(p.argmin()) + 1,
        )

    # Figure: Fig. 4 analogue
    dense = [0, 1, 2, 3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150]
    cls = chunked_means(space, dense, total // 4, 25000, 999)
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=130)
    for j, (name, col, ls) in enumerate(
        [("Switchy", "#2a78d6", "--"), ("Steady", "#eb6834", "-"), ("Sticky", "#1baf7a", ":")]
    ):
        ax.plot(
            dense, [cls[n][1][j] for n in dense], ls, color=col, lw=2.2, label=f"{name} (this code)"
        )
    paper = {20: (0.28, 0.57, 0.15), 50: (0.13, 0.84, 0.03)}
    for j, col in enumerate(["#2a78d6", "#eb6834", "#1baf7a"]):
        ax.scatter(
            [20, 50],
            [paper[20][j], paper[50][j]],
            s=70,
            facecolors="white",
            edgecolors=col,
            linewidths=2,
            zorder=5,
            label="printed in the paper's Section 4" if j == 0 else None,
        )
    ax.set_xlabel("Outcomes the learner has already seen")
    ax.set_ylabel("Mean posterior probability")
    ax.set_title(
        "Asymmetric convergence (paper's Fig. 4, top right)\nLines: our simulation. Circles: numbers printed in the paper.",
        fontsize=10,
    )
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="center right")
    fig.tight_layout()
    fig.savefig(RES / "fig_reproduction_fig4.png")
    plt.close(fig)

    # Figure: Fig. 6 analogue
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=130)
    cols = {25: "#d95f02", 40: "#1b9e77", 75: "#7570b3", 100: "#666666"}
    for n in (25, 40, 75, 100):
        ax.plot(
            range(1, 8),
            large[n][0][:7],
            "-",
            color=cols[n],
            lw=2,
            label=f"{n} outcomes seen (this code)",
        )
    for n in (25, 40):
        ax.scatter(
            range(1, 8),
            FIG6_BY_EYE[n],
            s=26,
            color=cols[n],
            marker="x",
            zorder=5,
            label=f"{n}: paper's Fig. 6, read by eye (about 0.01)" if n == 25 else f"{n}: same",
        )
    ax.scatter(
        [1, 3, 6],
        [0.485, 0.475, 0.55],
        s=70,
        facecolors="none",
        edgecolors="black",
        linewidths=1.6,
        zorder=6,
        label="40: printed in the text (Section 5.1)",
    )
    ax.axhline(0.5, color="grey", ls=":", lw=1)
    ax.set_xlabel("Length of the streak shown")
    ax.set_ylabel("Mean probability the streak continues")
    ax.set_title("Nonlinear expectations (paper's Fig. 6, top middle)", fontsize=10)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(RES / "fig_reproduction_fig6.png")
    plt.close(fig)

    # Figure: the new part, experience effect
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=130)
    shades = {
        0: "#d4cff6",
        10: "#a79fea",
        25: "#8a7fe0",
        40: "#6250d6",
        100: "#41359a",
        300: "#252060",
    }
    for n in (0, 10, 25, 40, 100, 300):
        ax.plot(range(1, 9), large[n][0], "-o", color=shades[n], lw=2, ms=3.5, label=f"{n} seen")
    ax.axhline(0.5, color="grey", ls=":", lw=1)
    ax.set_xlabel("Length of the streak shown")
    ax.set_ylabel("Mean probability the streak continues")
    ax.set_title(
        f"Less experience: the shift to expecting continuations comes sooner and is stronger\n(paper's model, default settings, {total} simulated learners per curve)",
        fontsize=9,
    )
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(RES / "fig_experience_effect.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
