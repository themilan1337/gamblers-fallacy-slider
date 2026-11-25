"""Check the colour tokens of docs/style.css against WCAG contrast thresholds.

Text colours (ink, ink-2, ink-3, accent) against bg and surface need 4.5; chart line colours
against surface need 3.0.  Writes results/contrast_report.csv and exits 1 on any failure.

    uv run python scripts/check_contrast.py
"""

import csv
import sys
from pathlib import Path

from gfmodel.contrast import contrast_ratio, parse_tokens

ROOT = Path(__file__).resolve().parents[1]
TEXT = ["ink", "ink-2", "ink-3", "accent"]
CHART = ["c-switchy", "c-steady", "c-sticky", "c-learner", "c-ref"]


def main() -> int:
    tokens = parse_tokens((ROOT / "docs" / "style.css").read_text(encoding="utf-8"))
    rows = []
    for theme in ("light", "dark_media", "dark"):
        t = tokens[theme]
        pairs = [(fg, bg, 4.5) for fg in TEXT for bg in ("bg", "surface")]
        pairs += [(fg, "surface", 3.0) for fg in CHART]
        for fg, bg, need in pairs:
            ratio = contrast_ratio(t[fg], t[bg])
            rows.append([theme, fg, t[fg], bg, t[bg], f"{ratio:.2f}", need, ratio >= need])
    out = ROOT / "results" / "contrast_report.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(
            ["theme", "foreground", "fg_hex", "background", "bg_hex", "ratio", "threshold", "pass"]
        )
        w.writerows(rows)
    bad = [r for r in rows if not r[-1]]
    for r in bad:
        print(f"FAIL {r[0]}: {r[1]} {r[2]} on {r[3]} {r[4]} = {r[5]} (needs {r[6]})")
    print(f"{len(rows)} pairs checked, {len(bad)} below threshold")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
