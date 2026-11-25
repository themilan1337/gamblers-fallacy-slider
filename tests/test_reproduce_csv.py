import csv

from gfmodel.reproduce import write_csv

FIELDS = [
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


def _rows():
    return [
        dict.fromkeys(FIELDS, "x") | {"id": "A1", "ours": 0.5},
        dict.fromkeys(FIELDS, "y") | {"id": "A2", "ours": 0.25},
    ]


def test_write_csv_uses_lf_only(tmp_path):
    path = tmp_path / "r.csv"
    write_csv(_rows(), path)
    assert b"\r" not in path.read_bytes()


def test_write_csv_round_trips_values(tmp_path):
    path = tmp_path / "r.csv"
    write_csv(_rows(), path)
    with open(path, newline="", encoding="utf-8") as f:
        got = list(csv.DictReader(f))
    assert [r["id"] for r in got] == ["A1", "A2"]
    assert [float(r["ours"]) for r in got] == [0.5, 0.25]
