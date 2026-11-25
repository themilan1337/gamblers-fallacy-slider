"""Run the Python-vs-JavaScript cross-check and write results/crosscheck_report.json.

uv run python scripts/crosscheck_report.py
"""

import json
from pathlib import Path

from gfmodel.crosscheck import run_all

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    report = run_all()
    report["tolerance_required"] = 1e-9
    (ROOT / "results" / "crosscheck_report.json").write_text(json.dumps(report, indent=2))
    print(report)
