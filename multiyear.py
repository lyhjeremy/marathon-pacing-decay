"""
multiyear.py - the 2014 decay curve, repeated for every Boston year with splits.

Reads ~/data-cache/marathon-pacing-decay/boston_splits.csv.gz (build_dataset.py)
and applies the same rules as analyze.load(): the 5, 10, 20, 25, 30, 35 and
40 km splits and the finish all present and strictly increasing. The one
difference from analyze.py is that wheelchair and handcycle entrants are
dropped by division rather than by the 5 km > 10 minutes filter, so the 2014
row here can differ slightly from tables/segment_pace.csv; both are reported.

Writes tables/years_decay.csv and tables/years_decay.json.
"""
import json, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.expanduser("~/data-cache/marathon-pacing-decay/boston_splits.csv.gz")
MARKS = ["k5", "k10", "k20", "k25", "k30", "k35", "k40", "finish"]
SEGS = [("0-5", 0, 5, None, "k5"), ("5-10", 5, 10, "k5", "k10"), ("10-20", 10, 20, "k10", "k20"),
        ("20-25", 20, 25, "k20", "k25"), ("25-30", 25, 30, "k25", "k30"), ("30-35", 30, 35, "k30", "k35"),
        ("35-40", 35, 40, "k35", "k40"), ("40-fin", 40, 42.195, "k40", "finish")]


def load_years():
    d = pd.read_csv(DATA, dtype={"bib": str})
    arr = d[MARKS].values
    ok = np.all(np.isfinite(arr), axis=1) & np.all(np.diff(arr, axis=1) > 0, axis=1)
    d = d[ok].copy()
    for lbl, a, b, ca, cb in SEGS:
        d[f"pace_{lbl}"] = (d[cb] - (d[ca] if ca else 0)) / (b - a)
    d["wall"] = (d["pace_35-40"] / d["pace_10-20"] - 1) * 100
    return d


def main():
    d = load_years()
    pc = [f"pace_{s[0]}" for s in SEGS]
    rows = []
    for y, g in d.groupby("year"):
        med = g[pc].median().values
        rel = (med / med[1] - 1) * 100
        rows.append({"year": int(y), "n": len(g), "median_finish_min": round(float(g["finish"].median()), 2),
                     **{f"pace_{s[0]}": round(float(m), 4) for s, m in zip(SEGS, med)},
                     **{f"rel_{s[0]}": round(float(r), 2) for s, r in zip(SEGS, rel)},
                     "median_wall_pct": round(float(g["wall"].median()), 2),
                     "share_wall_over_25pct": round(float((g["wall"] > 25).mean() * 100), 2),
                     "comparable": int(y != 2013)})
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(HERE, "tables", "years_decay.csv"), index=False)
    comp = t[t.comparable == 1]
    out = {"source": "boston_splits.csv.gz via multiyear.py; same split filter as analyze.load(), non-runner divisions dropped",
           "segments": [[s[0], s[1], s[2]] for s in SEGS],
           "years": [{"year": r.year, "n": r.n, "comparable": r.comparable, "median_finish": r.median_finish_min,
                      "pace": [r[f"pace_{s[0]}"] for s in SEGS], "wall_median": r.median_wall_pct,
                      "wall_over25": r.share_wall_over_25pct} for _, r in t.iterrows()],
           "range_comparable": {"wall_median": [float(comp.median_wall_pct.min()), float(comp.median_wall_pct.max())],
                                "wall_over25": [float(comp.share_wall_over_25pct.min()), float(comp.share_wall_over_25pct.max())]}}
    with open(os.path.join(HERE, "tables", "years_decay.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"), default=int)
    show = ["year", "n", "median_finish_min"] + [f"rel_{s[0]}" for s in SEGS] + ["median_wall_pct", "share_wall_over_25pct"]
    print(t[show].to_string(index=False))


if __name__ == "__main__":
    main()
