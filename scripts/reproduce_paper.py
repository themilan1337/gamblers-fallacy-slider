"""Reproduce the numbers in Dorst (2026) that this model should match; write results/reproduction.csv.

uv run python scripts/reproduce_paper.py            # full run, 25 s measured on Linux, 18 Oct 2026
uv run python scripts/reproduce_paper.py --quick    # fewer simulated learners
"""

import argparse
import sys
from pathlib import Path

from gfmodel.reproduce import run, write_csv

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "results" / "reproduction.csv"))
    args = ap.parse_args()
    rows = run(quick=args.quick)
    write_csv(rows, args.out)
    bad = [r for r in rows if not r["within_tolerance"]]
    for r in rows:
        flag = "ok  " if r["within_tolerance"] else "MISS"
        print(
            f"{flag} {r['id']:<10} paper {r['paper']:<7} ours {r['ours']:<8} (se {r['mc_se']}) {r['quantity']}"
        )
    print(f"\n{len(rows) - len(bad)} of {len(rows)} within tolerance; wrote {args.out}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
