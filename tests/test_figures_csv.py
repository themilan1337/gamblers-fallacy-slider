"""scripts/make_figures.py writes experience_curves.csv with LF only (no network, no plots run)."""

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_figures", ROOT / "scripts" / "make_figures.py")
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)

ROWS = [("a", 0, 1, 0.123456789), ("b", 10, 2, 0.5)]


def test_write_curves_csv_uses_lf_only(tmp_path):
    path = tmp_path / "c.csv"
    mf.write_curves_csv(path, ROWS)
    assert b"\r" not in path.read_bytes()


def test_write_curves_csv_rounds_and_round_trips(tmp_path):
    path = tmp_path / "c.csv"
    mf.write_curves_csv(path, ROWS)
    with open(path, newline="", encoding="utf-8") as f:
        got = list(csv.DictReader(f))
    assert [r["mean_p_continue"] for r in got] == ["0.12346", "0.5"]
    assert got[1]["source"] == "b" and got[1]["n_seen"] == "10"
