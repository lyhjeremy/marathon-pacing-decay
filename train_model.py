"""
train_model.py - fit, compare and export the in-race finish-time model.

Training years: 2014-2017 and 2021-2023. Holdout year: 2024, the latest year
with splits. Every choice below (model family, features, interval bins, number
of pacing types) is made from leave-one-year-out (LOYO) results on the training
years. 2024 is read only by evaluate(), after model/pace_model.json is written.

    python train_model.py compare   # LOYO comparison table only
    python train_model.py           # compare, fit, export JSON, evaluate on 2024

Writes model/pace_model.json, tables/model_compare.csv, tables/model_eval.json.
Needs scikit-learn and SciPy here; pace_model.py (inference) needs neither.
"""
import json, os, sys, time
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from scipy.optimize import linear_sum_assignment

import pace_model as pm

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.expanduser("~/data-cache/marathon-pacing-decay/boston_splits.csv.gz")
TRAIN_YEARS = [2014, 2015, 2016, 2017, 2021, 2022, 2023]
HOLDOUT = 2024
COLS = ["k5", "k10", "k15", "k20", "half", "k25", "k30", "k35", "k40"]
KM = np.array([5, 10, 15, 20, pm.HALF, 25, 30, 35, 40], dtype=float)
N_BINS = 5
QS = [0.025, 0.10, 0.50, 0.90, 0.975]
MODEL_VERSION = "2026-10-28.1"
RNG = np.random.default_rng(13)


def load(years):
    d = pd.read_csv(DATA, dtype={"bib": str})
    d = d[d["year"].isin(years) & (d["complete"] == 1) & d["gender"].isin(["M", "F"])].copy()
    d["female"] = (d["gender"] == "F").astype(float)
    T = d[COLS + ["finish"]].values
    T10, T20, T35, T40 = d["k10"].values, d["k20"].values, d["k35"].values, d["k40"].values
    d["wall"] = (((T40 - T35) / 5) / ((T20 - T10) / 10) > 1.25).astype(int)
    return d.reset_index(drop=True)


def at_checkpoint(d, c):
    """Rows usable at checkpoint c, the known-split matrix and the features."""
    j = int(np.where(np.isclose(KM, c))[0][0])
    km = KM[: j + 1]
    sub = d
    if c == 15.0:  # 2013/2014 have no 15 km split; interpolating it would use the 20 km time
        sub = d[d["k15"].notna()]
    T = sub[COLS[: j + 1]].values
    f, tc = pm.features_matrix(T, km, c, sub["female"].values, sub["age"].fillna(42).values)
    even = tc * pm.FULL / c
    y = np.log(sub["finish"].values / even)
    return sub.reset_index(drop=True), f, even, y


def ols(X, y, lam=1e-6):
    A = X.T @ X + lam * np.eye(X.shape[1])
    return np.linalg.solve(A, X.T @ y)


def median_fade_rule():
    """The repo's existing rule: scale the 2014 field's median pace profile."""
    P = json.load(open(os.path.join(HERE, "tables", "web_pacing.json")))
    segs, pace = P["segments"], P["field"]["pace"]
    x = [0.0] + [s[2] for s in segs]
    cum = np.concatenate([[0.0], np.cumsum([p * (s[2] - s[1]) for s, p in zip(segs, pace)])])
    return lambda c: float(cum[-1] / np.interp(c, x, cum))


def variant_rows(sub, variant):
    return np.isfinite(sub["age"].values) if "a" in variant else np.ones(len(sub), bool)


# ---------------------------------------------------------------- comparison
def compare(d):
    rule = median_fade_rule()
    rows = []
    for c in pm.CHECKPOINTS:
        sub, f, even, y = at_checkpoint(d, c)
        X = pm.design(f, "ga")
        Xr = np.column_stack([f[k] for k in pm.feature_names("ga")[:3] + ["female", "age10"]])
        fin = sub["finish"].values
        res = {"even": [], "fade_rule": [], "linear": [], "gbm": []}
        for yr in sorted(sub["year"].unique()):
            tr, te = (sub["year"] != yr).values, (sub["year"] == yr).values
            ok = tr & np.isfinite(sub["age"].values)
            b = ols(X[ok], y[ok])
            r = y[ok] - X[ok] @ b
            shift = np.median(r)
            idx = np.where(ok)[0]
            if len(idx) > 60000:
                idx = RNG.choice(idx, 60000, replace=False)
            g = HistGradientBoostingRegressor(loss="absolute_error", max_iter=200, learning_rate=0.1,
                                              max_leaf_nodes=31, min_samples_leaf=100, random_state=0)
            g.fit(Xr[idx], y[idx])
            e = even[te]
            res["even"].append(np.abs(e - fin[te]))
            res["fade_rule"].append(np.abs(e / pm.FULL * c * rule(c) - fin[te]))
            res["linear"].append(np.abs(e * np.exp(X[te] @ b + shift) - fin[te]))
            res["gbm"].append(np.abs(e * np.exp(g.predict(Xr[te])) - fin[te]))
        row = {"checkpoint_km": round(c, 4), "n": len(sub)}
        for k, v in res.items():
            row[f"loyo_mae_{k}"] = round(float(np.mean(np.concatenate(v))), 3)
        rows.append(row)
        print(row, flush=True)
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(HERE, "tables", "model_compare.csv"), index=False)
    return t


def compare_wall(d):
    rows = []
    for c in pm.CHECKPOINTS[:-1]:
        sub, f, even, y = at_checkpoint(d, c)
        X = pm.design(f, "ga")
        w = sub["wall"].values
        br = {"base_rate": [], "logistic": [], "gbm": []}
        for yr in sorted(sub["year"].unique()):
            tr, te = (sub["year"] != yr).values, (sub["year"] == yr).values
            lr = LogisticRegression(C=100, max_iter=2000).fit(X[tr][:, 1:], w[tr])
            idx = np.where(tr)[0]
            if len(idx) > 60000:
                idx = RNG.choice(idx, 60000, replace=False)
            g = HistGradientBoostingClassifier(max_iter=200, max_leaf_nodes=31, min_samples_leaf=100, random_state=0).fit(X[idx][:, 1:], w[idx])
            br["base_rate"].append((w[tr].mean() - w[te]) ** 2)
            br["logistic"].append((lr.predict_proba(X[te][:, 1:])[:, 1] - w[te]) ** 2)
            br["gbm"].append((g.predict_proba(X[te][:, 1:])[:, 1] - w[te]) ** 2)
        row = {"checkpoint_km": round(c, 4), **{f"loyo_brier_{k}": round(float(np.mean(np.concatenate(v))), 4) for k, v in br.items()}}
        rows.append(row)
        print(row, flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- final fit
def fit_checkpoint(d, c):
    sub, f, even, y = at_checkpoint(d, c)
    fa = f["f_avg"]
    edges = np.quantile(fa, np.linspace(0, 1, N_BINS + 1)[1:-1]).tolist()
    bins = np.searchsorted(edges, fa, side="right")
    out = {"n": int(len(sub)), "years": sorted(int(v) for v in sub["year"].unique()), "bins": [round(e, 6) for e in edges],
           "finish": {}, "wall": {}}
    for v in pm.VARIANTS:
        ok = variant_rows(sub, v)
        X = pm.design(f, v)
        # out-of-year residuals for the conformal quantiles
        oof = np.full(len(sub), np.nan)
        for yr in sorted(sub["year"].unique()):
            tr, te = ok & (sub["year"] != yr).values, ok & (sub["year"] == yr).values
            b = ols(X[tr], y[tr])
            oof[te] = y[te] - X[te] @ b
        b = ols(X[ok], y[ok])
        rq = []
        for k in range(N_BINS):
            r = oof[ok & (bins == k)]
            n = len(r)
            # finite-sample split-conformal levels for each one-sided quantile
            lv = [min(1, max(0, np.ceil((n + 1) * q) / n)) if q > 0.5 else max(0, np.floor((n + 1) * q) / n) for q in QS]
            rq.append([round(float(np.quantile(r, l)), 6) for l in lv])
        out["finish"][v] = {"coef": [round(float(x), 8) for x in b], "features": pm.feature_names(v), "resid_q": rq,
                            "n_calib": int(ok.sum())}
        if c < 40:
            lr = LogisticRegression(C=100, max_iter=3000).fit(X[ok][:, 1:], sub["wall"].values[ok])
            out["wall"][v] = {"coef": [round(float(lr.intercept_[0]), 8)] + [round(float(x), 8) for x in lr.coef_[0]]}
    return out


def type_matrix(d):
    lens = np.array([b - a for a, b in pm.TYPE_SEGS])
    cols = ["k5", "k10", "k20", "k25", "k30", "k35", "k40", "finish"]
    T = np.hstack([np.zeros((len(d), 1)), d[cols].values])
    pace = np.diff(T, axis=1) / lens
    prof = pace / (d["finish"].values[:, None] / pm.FULL)
    return prof, np.sqrt(lens / lens.sum())


def fit_types(d, k_final=None):
    prof, w = type_matrix(d)
    # clip so a handful of runners who stopped for a long time cannot pull a centroid
    Z = np.clip(prof, 0.7, 1.8) * w
    sample = RNG.choice(len(Z), min(40000, len(Z)), replace=False)
    report = []
    for k in range(3, 7):
        labs = [KMeans(k, n_init=10, random_state=s).fit(Z[sample]).labels_ for s in range(5)]
        ari = np.mean([adjusted_rand_score(labs[0], l) for l in labs[1:]])
        sil = silhouette_score(Z[sample][:10000], labs[0][:10000])
        report.append({"k": k, "seed_ari": round(float(ari), 3), "silhouette": round(float(sil), 3)})
        print(report[-1], flush=True)
    k = k_final or 4
    km = KMeans(k, n_init=20, random_state=0).fit(Z)
    cen = km.cluster_centers_ / w
    # order by late-race slowdown (35-40 against 10-20)
    order = np.argsort(cen[:, 6] / cen[:, 2])
    cen = cen[order]
    lab = np.argsort(order)[km.labels_]
    # year stability: fit each year alone, match centroids to the pooled ones
    yr_rows = []
    for yr in sorted(d["year"].unique()):
        m = (d["year"] == yr).values
        kmy = KMeans(k, n_init=10, random_state=0).fit(Z[m])
        cy = kmy.cluster_centers_ / w
        cost = np.array([[np.abs(a - b).max() for b in cy] for a in cen])
        ri, ci = linear_sum_assignment(cost)
        # agreement between this year's own clustering and the pooled one
        mapped = np.empty(k, int); mapped[ci] = ri
        agree = float((mapped[kmy.labels_] == lab[m]).mean())
        yr_rows.append({"year": int(yr), "max_centroid_gap": round(float(cost[ri, ci].max()), 4), "label_agreement": round(agree, 3),
                        "shares": [round(float((lab[m] == j).mean() * 100), 1) for j in range(k)]})
        print(yr_rows[-1], flush=True)
    return cen, lab, report, yr_rows


TYPE_NAMES = {
    4: ["Even", "Steady fade", "Hill fade", "Hit the wall"],
}


def name_types(cen):
    """Names follow the order fit_types sorts by (late against mid-race pace)."""
    k = len(cen)
    names = TYPE_NAMES.get(k, [f"Type {i + 1}" for i in range(k)])
    desc = []
    for c in cen:
        desc.append(f"0-10 km {100 * (np.mean(c[:2]) - 1):+.1f}%, 10-25 km {100 * (np.average(c[2:4], weights=[10, 5]) - 1):+.1f}%, "
                    f"25-35 km {100 * (np.mean(c[4:6]) - 1):+.1f}%, 35 km-finish {100 * (np.average(c[6:], weights=[5, 2.195]) - 1):+.1f}% against own mean pace")
    return names, desc


# ---------------------------------------------------------------- holdout
def evaluate(model):
    d = load([HOLDOUT])
    rule = median_fade_rule()
    out = {"holdout_year": HOLDOUT, "n_runners": int(len(d)), "checkpoints": [], "wall": {}, "types": {}}
    wall_pred, wall_true, med_pred = {}, {}, {}
    for c in pm.CHECKPOINTS:
        sub, f, even, y = at_checkpoint(d, c)
        ck = model["checkpoints"][f"{c:g}"]
        X = pm.design(f, "ga")
        okv = np.isfinite(sub["age"].values)
        fin = sub["finish"].values
        rows = {}
        for v in ("ga", "none"):
            fm = ck["finish"][v]
            Xv = pm.design(f, v)
            yh = Xv @ np.array(fm["coef"])
            b = np.searchsorted(ck["bins"], f["f_avg"], side="right")
            q = np.array(fm["resid_q"])[b]
            pred = even[:, None] * np.exp(yh[:, None] + q)
            m = okv if v == "ga" else np.ones(len(sub), bool)
            if v == "none":
                med_pred[c] = pred[:, 2]
            rows[v] = {"mae": float(np.mean(np.abs(pred[m, 2] - fin[m]))),
                       "cov80": float(np.mean((fin[m] >= pred[m, 1]) & (fin[m] <= pred[m, 3]))),
                       "cov95": float(np.mean((fin[m] >= pred[m, 0]) & (fin[m] <= pred[m, 4]))),
                       "width80": float(np.median(pred[m, 3] - pred[m, 1])),
                       "width95": float(np.median(pred[m, 4] - pred[m, 0]))}
            if v == "ga":
                # coverage by finish band, to see where intervals miss
                band = np.digitize(fin[m], [180, 210, 240, 270, 300])
                rows[v]["cov80_by_band"] = [round(float(np.mean(((fin[m] >= pred[m, 1]) & (fin[m] <= pred[m, 3]))[band == i])), 3) for i in range(6)]
        row = {"checkpoint_km": round(c, 4), "n": int(okv.sum()),
               "mae_even": round(float(np.mean(np.abs(even[okv] - fin[okv]))), 3),
               "mae_fade_rule": round(float(np.mean(np.abs(even[okv] / pm.FULL * c * rule(c) - fin[okv]))), 3),
               "mae_model": round(rows["ga"]["mae"], 3), "mae_model_no_demographics": round(rows["none"]["mae"], 3),
               "cov80": round(rows["ga"]["cov80"], 4), "cov95": round(rows["ga"]["cov95"], 4),
               "cov80_no_demographics": round(rows["none"]["cov80"], 4), "cov95_no_demographics": round(rows["none"]["cov95"], 4),
               "median_width80": round(rows["ga"]["width80"], 2), "median_width95": round(rows["ga"]["width95"], 2),
               "cov80_by_finish_band": rows["ga"]["cov80_by_band"]}
        if c < 40:
            p = 1 / (1 + np.exp(-(X[okv] @ np.array(ck["wall"]["ga"]["coef"]))))
            wall_pred[c], wall_true[c] = p, sub["wall"].values[okv]
            row["brier_wall"] = round(float(np.mean((p - wall_true[c]) ** 2)), 4)
            base = model["wall_base_rate"]
            row["brier_wall_base_rate"] = round(float(np.mean((base - wall_true[c]) ** 2)), 4)
        out["checkpoints"].append(row)
        print(row, flush=True)
    out["wall"]["holdout_rate"] = round(float(d["wall"].mean()), 4)
    out["wall"]["train_base_rate"] = model["wall_base_rate"]
    rel = {}
    for c in (10.0, pm.HALF, 30.0, 35.0):
        p, t = wall_pred[c], wall_true[c]
        b = np.minimum((p * 10).astype(int), 9)
        rel[f"{c:g}"] = [{"bin": f"{i / 10:.1f}-{(i + 1) / 10:.1f}", "n": int((b == i).sum()),
                          "mean_pred": round(float(p[b == i].mean()), 4) if (b == i).any() else None,
                          "observed": round(float(t[b == i].mean()), 4) if (b == i).any() else None} for i in range(10)]
    out["wall"]["reliability"] = rel
    # pacing types on the holdout: full-race shares, and how often the type
    # from the splits seen so far matches the full-race type
    prof, w = type_matrix(d)
    cen = np.array(model["types"]["centroids"])
    lens = np.array([b - a for a, b in pm.TYPE_SEGS])
    full = np.argmin((((prof[:, None, :] - cen[None]) ** 2) * lens).sum(-1), axis=1)
    out["types"]["shares_pct"] = [round(float((full == j).mean() * 100), 1) for j in range(len(cen))]
    match = {}
    for c in pm.CHECKPOINTS:
        segs = [i for i, (a, b) in enumerate(pm.TYPE_SEGS) if b <= c + 1e-9]
        L = lens[segs]
        # same rule as pace_model.type_profile: seen paces over the predicted mean pace
        p = prof[:, segs] * (d["finish"].values / med_pred[c])[:, None]
        part = np.argmin((((p[:, None, :] - cen[None][:, :, segs]) ** 2) * L).sum(-1), axis=1)
        match[f"{c:g}"] = round(float((part == full).mean()), 3)
    out["types"]["match_full_race_by_checkpoint"] = match
    out["types"]["match_if_always_most_common"] = round(float(np.bincount(full).max() / len(full)), 3)
    # the scalar predict_finish() path against the vectorized path, on 300 runners
    sub, f, even, y = at_checkpoint(d, 25.0)
    ck = model["checkpoints"]["25"]
    fm = ck["finish"]["ga"]
    b = np.searchsorted(ck["bins"], f["f_avg"], side="right")
    vec = even * np.exp(pm.design(f, "ga") @ np.array(fm["coef"]) + np.array(fm["resid_q"])[b][:, 2])
    diffs = []
    for i in RNG.choice(np.where(np.isfinite(sub["age"].values))[0], 300, replace=False):
        r = sub.iloc[i]
        sp = {5: r.k5, 10: r.k10, 15: r.k15, 20: r.k20, 21: r.half, 25: r.k25}
        a = pm.predict_finish(sp, r.gender, int(r.age))
        diffs.append(abs(a["median_min"] - vec[i]))
    out["scalar_path_check"] = {"runners": len(diffs), "max_abs_diff_min": round(float(max(diffs)), 4)}
    # sparse input: only 10 km and the half known, against all splits to the half
    sub, f, even, y = at_checkpoint(d, pm.HALF)
    T = sub[["k10", "half"]].values
    f2, tc = pm.features_matrix(T, np.array([10, pm.HALF]), pm.HALF, sub["female"].values, sub["age"].fillna(42).values)
    ck = model["checkpoints"][f"{pm.HALF:g}"]["finish"]["ga"]
    b = np.searchsorted(model["checkpoints"][f"{pm.HALF:g}"]["bins"], f2["f_avg"], side="right")
    pred = tc * pm.FULL / pm.HALF * np.exp(pm.design(f2, "ga") @ np.array(ck["coef"]) + np.array(ck["resid_q"])[b][:, 2])
    out["sparse_half_10k_only_mae"] = round(float(np.mean(np.abs(pred - sub["finish"].values))), 3)
    return out


def gbm_on_holdout(d_train):
    """Recorded after the choice was locked by LOYO: the rejected boosted-tree
    model scored on 2024, so the page can say whether the choice held up."""
    d = load([HOLDOUT])
    rows = []
    for c in pm.CHECKPOINTS:
        sub, f, even, y = at_checkpoint(d_train, c)
        Xr = np.column_stack([f[k] for k in pm.feature_names("ga")[:3] + ["female", "age10"]])
        idx = RNG.choice(len(sub), min(60000, len(sub)), replace=False)
        g = HistGradientBoostingRegressor(loss="absolute_error", max_iter=200, learning_rate=0.1,
                                          max_leaf_nodes=31, min_samples_leaf=100, random_state=0).fit(Xr[idx], y[idx])
        hs, hf, he, hy = at_checkpoint(d, c)
        ok = np.isfinite(hs["age"].values)
        Xh = np.column_stack([hf[k] for k in pm.feature_names("ga")[:3] + ["female", "age10"]])
        rows.append({"checkpoint_km": round(c, 4), "mae_gbm": round(float(np.mean(np.abs(he[ok] * np.exp(g.predict(Xh[ok])) - hs["finish"].values[ok]))), 3)})
    return rows


def main():
    d = load(TRAIN_YEARS)
    print(f"training runners: {len(d):,} across {sorted(d.year.unique())}")
    t0 = time.time()
    cmp_ = compare(d)
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        print(compare_wall(d))
        return
    wall_cmp = compare_wall(d)
    cmp_ = cmp_.merge(wall_cmp, on="checkpoint_km", how="left")
    cmp_.to_csv(os.path.join(HERE, "tables", "model_compare.csv"), index=False)
    cen, lab, kreport, yr_rows = fit_types(d)
    names, desc = name_types(cen)
    model = {"model_version": MODEL_VERSION, "n_train": int(len(d)), "train_years": TRAIN_YEARS, "holdout_year": HOLDOUT,
             "target": "log(finish / even-pace projection from the latest split)",
             "intervals": "split conformal, Mondrian by 5 bins of current average pace, calibrated on leave-one-year-out residuals",
             "wall_definition": "35-40 km pace more than 25% slower than the runner's own 10-20 km pace",
             "wall_base_rate": round(float(d["wall"].mean()), 4),
             "quantiles": QS, "checkpoints": {}, "variants": pm.VARIANTS}
    for c in pm.CHECKPOINTS:
        model["checkpoints"][f"{c:g}"] = fit_checkpoint(d, c)
        print("fit", c, flush=True)
    model["types"] = {"segments": [[a, b] for a, b in pm.TYPE_SEGS], "centroids": [[round(float(x), 5) for x in c] for c in cen],
                      "names": names, "shape": desc,
                      "train_shares_pct": [round(float((lab == j).mean() * 100), 1) for j in range(len(cen))],
                      "k_search": kreport, "year_stability": yr_rows}
    os.makedirs(os.path.join(HERE, "model"), exist_ok=True)
    with open(pm.JSON_PATH, "w") as f:
        json.dump(model, f, separators=(",", ":"))
    pm._MODEL = None
    print(f"wrote {pm.JSON_PATH} ({os.path.getsize(pm.JSON_PATH):,} bytes)")
    ev = evaluate(model)
    ev["loyo_compare"] = cmp_.to_dict(orient="records")
    ev["holdout_gbm_after_choice"] = gbm_on_holdout(d)
    with open(os.path.join(HERE, "tables", "model_eval.json"), "w") as f:
        json.dump(ev, f, indent=1)
    print(json.dumps({k: v for k, v in ev.items() if k not in ("checkpoints", "loyo_compare")}, indent=1)[:3000])
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
