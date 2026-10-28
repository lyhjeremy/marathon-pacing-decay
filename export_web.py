"""
export_web.py - aggregates for the interactive charts on the write-up page.
Reads the race through analyze.load(), so segments and filters match
analyze.py exactly; it changes no result. Writes tables/web_pacing.json.
"""
import json, os
import numpy as np
from analyze import load, SEGS, HERE

PACE = [f"pace_{s[0]}" for s in SEGS]


def med(d):
    return [round(float(v), 4) for v in d[PACE].median().values]


def main():
    df = load()
    df["wall"] = (df["pace_35-40"] / df["pace_10-20"] - 1) * 100
    groups = [("Sub-3:00", df.finish_h < 3), ("3:00-3:30", (df.finish_h >= 3) & (df.finish_h < 3.5)),
              ("3:30-4:00", (df.finish_h >= 3.5) & (df.finish_h < 4)), ("4:00-4:30", (df.finish_h >= 4) & (df.finish_h < 4.5)),
              ("Over 4:30", df.finish_h >= 4.5)]
    out = {"source": "data/boston_2014.csv via analyze.load()",
           "segments": [[s[0], s[1], s[2]] for s in SEGS],
           "field": {"n": int(len(df)), "pace": med(df)},
           "groups": [{"label": g, "n": int(m.sum()), "pace": med(df[m])} for g, m in groups],
           "bands": [],
           "wall": {"median": round(float(df["wall"].median()), 2), "over25": round(float((df["wall"] > 25).mean() * 100), 2),
                    "bins": "1% bins from -10 to 80, values clipped into the end bins",
                    "hist": np.histogram(np.clip(df["wall"].values, -10, 80), bins=np.arange(-10, 81, 1))[0].tolist()}}
    for lo in range(135, 360, 15):  # 15-minute finish bands, 2:15 to 6:00
        m = (df.official >= lo) & (df.official < lo + 15)
        if m.sum() >= 50:
            out["bands"].append({"lo": lo, "hi": lo + 15, "n": int(m.sum()), "pace": med(df[m])})
    with open(os.path.join(HERE, "tables", "web_pacing.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(out["field"], out["wall"]["median"], out["wall"]["over25"])
    for g in out["groups"]:
        p = g["pace"]; print(g["label"], g["n"], [round((x / p[1] - 1) * 100, 1) for x in p])
    print([(b["lo"], b["n"]) for b in out["bands"]])


if __name__ == "__main__":
    main()
