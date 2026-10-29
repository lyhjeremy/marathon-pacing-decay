"""
build_dataset.py - one table of Boston Marathon splits across years.

Reads the raw files fetch_multiyear.py downloaded and writes
~/data-cache/marathon-pacing-decay/boston_splits.csv.gz (not committed) plus the
per-year row counts in tables/years.csv (committed).

Every split is cumulative net time in decimal minutes. Columns:
  year, source, bib, gender (M/F), age, k5, k10, k15, k20, half, k25, k30, k35,
  k40, finish, complete
`complete` is 1 when every split that year's source carries is present and the
times strictly increase. 2013 and 2014 have no 15 km split, so k15 is empty for
them and `complete` ignores it.

Entrants dropped: wheelchair, handcycle and duo divisions (bib prefix W or H in
the 2013-2017 files, the division column in 2021-2024), and, as a backstop,
anyone whose 5 km split is under 13 minutes or finish under 2 hours.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser("~/data-cache/marathon-pacing-decay")
RAW = os.path.join(CACHE, "raw")
OUT = os.path.join(CACHE, "boston_splits.csv.gz")
SPLITS = ["k5", "k10", "k15", "k20", "half", "k25", "k30", "k35", "k40", "finish"]
KM = {"k5": 5, "k10": 10, "k15": 15, "k20": 20, "half": 21.0975, "k25": 25, "k30": 30, "k35": 35, "k40": 40, "finish": 42.195}


def hms(s):
    """'h:mm:ss' (or '-' / blank) to decimal minutes."""
    def one(v):
        if not isinstance(v, str) or ":" not in v:
            return np.nan
        p = [float(x) for x in v.strip().split(":")]
        return p[0] * 60 + p[1] + p[2] / 60 if len(p) == 3 else p[0] + p[1] / 60
    return s.map(one)


def from_llimllib(year):
    d = pd.read_csv(os.path.join(RAW, "llimllib", f"results_{year}.csv"), dtype=str)
    n_raw = len(d)
    out = pd.DataFrame({"year": year, "source": "llimllib/bostonmarathon", "bib": d["bib"].str.strip(),
                        "gender": d["gender"].str.upper().str[0], "age": pd.to_numeric(d["age"], errors="coerce")})
    for col, src in [("k5", "5k"), ("k10", "10k"), ("k20", "20k"), ("half", "half"), ("k25", "25k"),
                     ("k30", "30k"), ("k35", "35k"), ("k40", "40k"), ("finish", "official")]:
        out[col] = pd.to_numeric(d[src], errors="coerce")
    out["k15"] = np.nan
    return out, n_raw


def from_kaggle(year):
    d = pd.read_csv(os.path.join(RAW, "kaggle", f"marathon_results_{year}.csv"), dtype=str)
    n_raw = len(d)
    out = pd.DataFrame({"year": year, "source": "Kaggle mirror (Marc-Bouche/boston-marathon-analysis)",
                        "bib": d["Bib"].str.strip(), "gender": d["M/F"].str.upper().str[0],
                        "age": pd.to_numeric(d["Age"], errors="coerce")})
    for col, src in [("k5", "5K"), ("k10", "10K"), ("k15", "15K"), ("k20", "20K"), ("half", "Half"), ("k25", "25K"),
                     ("k30", "30K"), ("k35", "35K"), ("k40", "40K"), ("finish", "Official Time")]:
        out[col] = hms(d[src])
    return out, n_raw


def from_williamsorg4():
    import pyreadr  # training-time dependency only
    d = pyreadr.read_r(os.path.join(RAW, "williamsorg4", "allresults.rds"))[None]
    pts = {"fiveK": "k5", "tenK": "k10", "fifteenK": "k15", "twentyK": "k20", "HALF": "half", "twentyfiveK": "k25",
           "thirtyK": "k30", "thirtyfiveK": "k35", "fortyK": "k40", "FINISH": "finish"}
    d = d[d["point"].isin(pts)]
    w = d.pivot_table(index=["year", "pid"], columns="point", values="time", aggfunc="first").rename(columns=pts) / 60
    meta = d.drop_duplicates(["year", "pid"]).set_index(["year", "pid"])[["bib", "sex", "age", "division"]]
    w = w.join(meta).reset_index()
    frames, raws = {}, {}
    for y, g in w.groupby("year"):
        y = int(y)
        raws[y] = len(g)
        keep = g[g["division"] == "runner"]
        out = pd.DataFrame({"year": y, "source": "williamsorg4/BostonMarathonTimeModel", "bib": keep["bib"].astype(str),
                            "gender": keep["sex"].str.upper().str[0].replace({"W": "F"}),
                            "age": pd.to_numeric(keep["age"], errors="coerce")})
        for c in SPLITS:
            out[c] = keep[c].values
        out.attrs["dropped_division"] = int((g["division"] != "runner").sum())
        frames[y] = out
    return frames, raws


def clean(out):
    out = out.copy()
    nonrunner = out["bib"].str.upper().str.match(r"^[WH]") if out["source"].iloc[0] != "williamsorg4/BostonMarathonTimeModel" else pd.Series(False, index=out.index)
    n_nonrunner = int(nonrunner.sum()) + out.attrs.get("dropped_division", 0)
    out = out[~nonrunner]
    fast = (out["k5"] < 13) | (out["finish"] < 120)
    n_fast = int(fast.sum())
    out = out[~fast & out["finish"].notna()]
    marks = [c for c in SPLITS if out[c].notna().any()]
    arr = out[marks].values
    out["complete"] = (np.all(np.isfinite(arr), axis=1) & np.all(np.diff(arr, axis=1) > 0, axis=1)).astype(int)
    out["gender"] = out["gender"].where(out["gender"].isin(["M", "F"]))
    return out, n_nonrunner, n_fast


def main():
    rows, counts = [], []
    parts = []
    for y in (2013, 2014):
        parts.append((y, *from_llimllib(y)))
    for y in (2015, 2016, 2017):
        parts.append((y, *from_kaggle(y)))
    wf, wr = from_williamsorg4()
    for y in sorted(wf):
        parts.append((y, wf[y], wr[y]))
    for y, df, n_raw in parts:
        df, n_nonrunner, n_fast = clean(df)
        rows.append(df)
        counts.append({"year": y, "source": df["source"].iloc[0], "rows_in_source": n_raw,
                       "wheelchair_handcycle_duo_dropped": n_nonrunner, "speed_backstop_dropped": n_fast,
                       "finishers": len(df), "complete_splits": int(df["complete"].sum()),
                       "has_15k": int(df["k15"].notna().any()),
                       "note": "race halted at 4:09 gun time; finishers biased fast; excluded from model and year comparisons" if y == 2013 else ""})
    all_ = pd.concat(rows, ignore_index=True)
    all_ = all_[["year", "source", "bib", "gender", "age"] + SPLITS + ["complete"]]
    os.makedirs(CACHE, exist_ok=True)
    all_.to_csv(OUT, index=False, float_format="%.4f", compression="gzip")
    c = pd.DataFrame(counts)
    c.to_csv(os.path.join(HERE, "tables", "years.csv"), index=False)
    print(c.to_string(index=False))
    print(f"wrote {OUT} ({len(all_):,} rows)")


if __name__ == "__main__":
    main()
