"""
analyze.py - Hitting the Wall: the marathon pacing-decay curve (Boston 2014)
============================================================================
Using per-5K timing splits, we trace how fast each runner was going through the
race and show where the field slows down - the famous "wall" in the last 10 km.

Splits are cumulative times in decimal minutes. We convert each segment to a pace
in minutes per kilometre and look at how pace evolves with distance.

Outputs: figures/*.png and tables/summary.csv
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
FIG = os.path.join(HERE, "figures"); TAB = os.path.join(HERE, "tables")
INK, GOLD, TEAL, CORAL, GREEN, PLUM = "#1a1a2e", "#D4A537", "#15868C", "#E0567A", "#1f9d6b", "#5B4B8A"
plt.rcParams.update({"figure.dpi": 200, "savefig.dpi": 200, "font.size": 12,
    "axes.edgecolor": "#888", "axes.grid": True, "grid.color": "#e8e2d4",
    "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white"})

# cumulative marks (km) available in the 2014 file
MARKS = [("5k", 5), ("10k", 10), ("20k", 20), ("25k", 25), ("30k", 30), ("35k", 35), ("40k", 40), ("official", 42.195)]
# segments as (label, from_km, to_km, from_col, to_col)
SEGS = [("0-5", 0, 5, None, "5k"), ("5-10", 5, 10, "5k", "10k"), ("10-20", 10, 20, "10k", "20k"),
        ("20-25", 20, 25, "20k", "25k"), ("25-30", 25, 30, "25k", "30k"), ("30-35", 30, 35, "30k", "35k"),
        ("35-40", 35, 40, "35k", "40k"), ("40-fin", 40, 42.195, "40k", "official")]
MID = [2.5, 7.5, 15, 22.5, 27.5, 32.5, 37.5, 41.1]


def load():
    df = pd.read_csv(os.path.join(HERE, "data", "boston_2014.csv"))
    cols = [c for c, _ in MARKS]
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=cols)
    # require strictly increasing cumulative times
    arr = df[cols].values
    ok = np.all(np.diff(arr, axis=1) > 0, axis=1)
    df = df[ok & (df["5k"] > 10)]
    # per-segment pace (min/km)
    for lbl, a, b, ca, cb in SEGS:
        t = df[cb] - (df[ca] if ca else 0)
        df[f"pace_{lbl}"] = t / (b - a)
    df["finish_h"] = df["official"] / 60
    df["gender"] = df["gender"].astype(str).str.upper().str[0]
    return df


def main():
    os.makedirs(FIG, exist_ok=True); os.makedirs(TAB, exist_ok=True)
    df = load()
    pace_cols = [f"pace_{s[0]}" for s in SEGS]
    print(f"Runners with full splits: {len(df):,}")

    med = df[pace_cols].median().values
    base = med[1]  # 5-10k pace as "settled" baseline
    decay_pct = (med / base - 1) * 100
    for (lbl, *_), m, d in zip(SEGS, med, decay_pct):
        print(f"  {lbl:8} {m:5.2f} min/km   {d:+5.1f}% vs 5-10k")

    # wall metric: 35-40k vs 10-20k
    df["wall"] = (df["pace_35-40"] / df["pace_10-20"] - 1) * 100
    wall_med = df["wall"].median()
    big_wall = (df["wall"] > 25).mean() * 100
    print(f"Median late slowdown (35-40k vs 10-20k): {wall_med:.1f}%")
    print(f"Share whose late pace was >25% slower:   {big_wall:.1f}%")

    # ---- Fig 1: the decay curve ----
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.plot(MID, med, "-o", color=TEAL, lw=2.6, ms=7)
    ax.axvspan(32, 42.195, color=CORAL, alpha=0.08)
    ax.axvline(32, color=CORAL, ls="--", lw=2)
    ax.text(33, ax.get_ylim()[1], "  'the wall'\n  (~32 km)", color=CORAL, va="top", fontsize=11)
    ax.set_xlabel("Distance into the race (km)"); ax.set_ylabel("Median pace (min/km) — higher = slower")
    ax.set_title("The marathon pacing-decay curve", color=INK, weight="bold")
    fig.tight_layout(); fig.savefig(f"{FIG}/01_decay_curve.png"); plt.close(fig)

    # ---- Fig 2: by finish-time group, relative to own early pace ----
    groups = [("Sub-3:00", df.finish_h < 3, GREEN), ("3:00-3:30", (df.finish_h >= 3) & (df.finish_h < 3.5), TEAL),
              ("3:30-4:00", (df.finish_h >= 3.5) & (df.finish_h < 4), GOLD),
              ("4:00-4:30", (df.finish_h >= 4) & (df.finish_h < 4.5), "#d98324"),
              ("Over 4:30", df.finish_h >= 4.5, CORAL)]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for name, mask, col in groups:
        sub = df[mask]
        if len(sub) < 30: continue
        m = sub[pace_cols].median().values
        rel = (m / m[1] - 1) * 100  # vs own 5-10k pace
        ax.plot(MID, rel, "-o", color=col, lw=2.2, ms=5, label=f"{name} (n={len(sub):,})")
    ax.axvline(32, color="#aaa", ls="--", lw=1.5)
    ax.set_xlabel("Distance into the race (km)"); ax.set_ylabel("Slowdown vs own early pace (%)")
    ax.set_title("Everyone slows late — slower runners slow much more", color=INK, weight="bold")
    ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(f"{FIG}/02_decay_by_group.png"); plt.close(fig)

    # ---- Fig 3: distribution of the late-race wall ----
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.hist(df["wall"].clip(-10, 80), bins=80, color=PLUM, alpha=0.85)
    ax.axvline(0, color=INK, ls="--", lw=2, label="no slowdown")
    ax.axvline(wall_med, color=CORAL, lw=2, label=f"median +{wall_med:.0f}%")
    ax.set_xlabel("How much slower the 35–40 km pace was vs 10–20 km (%)"); ax.set_ylabel("Runners")
    ax.set_title("How hard the wall hits", color=INK, weight="bold"); ax.legend()
    fig.tight_layout(); fig.savefig(f"{FIG}/03_wall_distribution.png"); plt.close(fig)

    summary = pd.DataFrame({"segment": [s[0] for s in SEGS],
                            "median_pace_min_per_km": np.round(med, 3),
                            "pct_vs_5_10k": np.round(decay_pct, 2)})
    summary.to_csv(f"{TAB}/segment_pace.csv", index=False)
    pd.DataFrame({"metric": ["runners", "median_late_slowdown_pct", "share_wall_over_25pct"],
                  "value": [len(df), round(wall_med, 2), round(big_wall, 2)]}).to_csv(f"{TAB}/summary.csv", index=False)
    print("\nSaved figures + tables/")


if __name__ == "__main__":
    main()
