# Hitting the Wall: the marathon pacing-decay curve

Where does a marathon field slow down? This repo measures it from the 5 km splits of 31,655 finishers of the 2014 Boston Marathon; the answer is a bend that starts after 25 km. Since October 2026 it also repeats that curve for every Boston year with public splits (2014 to 2017, 2021 to 2024) and ships an in-race model: give it the splits you have so far and it predicts your finish with 80% and 95% ranges, your chance of hitting the wall, and your pacing type. The [live split tool](https://lyhjeremy.github.io/marathon-pacing-decay/#tool) runs it in the browser.

[Live site](https://lyhjeremy.github.io/marathon-pacing-decay/) · [Write-up](https://lyhjeremy.github.io/marathon-pacing-decay/overview/)

Design and copy follow [these standards](https://github.com/lyhjeremy/lyhjeremy/blob/main/DESIGN_STANDARDS.md).

## Results

- Median pace is close to flat through 20 km (+2.4% against the 5 to 10 km pace), then rises to +12.9% at 25 to 30 km and +19.4% at 30 to 35 km.
- The median runner's 35 to 40 km pace was **15%** slower than their own 10 to 20 km pace.
- **27%** of finishers slowed by more than 25% on that comparison.
- Against their own 5 to 10 km pace, runners under 3:00 end 8 to 9% slower; runners over 4:30 are 33 to 35% slower between 30 and 40 km.

The [write-up](https://lyhjeremy.github.io/marathon-pacing-decay/overview/#plan) has a split card: enter a finish time and it shows the splits that Boston 2014 runners within the same 15 minutes ran, scaled to that time, next to even pace.

![Median pace by distance for the 2014 Boston field: near 5.0 min/km through 10 km, rising steeply to about 6.1 min/km between 30 and 40 km](figures/01_decay_curve.png)

| Segment | Median pace (min/km) | vs 5 to 10 km |
|---|---|---|
| 0–5 km | 5.01 | −0.6% |
| 5–10 km | 5.04 | 0.0% |
| 10–20 km | 5.17 | +2.4% |
| 20–25 km | 5.35 | +6.1% |
| 25–30 km | 5.69 | +12.9% |
| 30–35 km | 6.02 | +19.4% |
| 35–40 km | 6.09 | +20.7% |
| 40 km–finish | 6.00 | +19.0% |

From `tables/segment_pace.csv`.

## October 2026 upgrade: eight years and a predictor

The 2014 numbers above are unchanged. The upgrade adds:

**Per-year curves** (`tables/years_decay.csv`). The corner sits between 25 and 35 km in every year, but 2014 had the hardest fade of the eight comparable years. Its median late slowdown was 15.1% with 27.4% of runners over +25%; the other years ranged from 5.7% and 7.5% (2023) to 13.2% and 22.7% (2024). 2013 is computed but excluded from comparisons because the race was halted at about 4:09 on the race clock, so only the faster part of the field finished.

| Year | Finishers (full splits) | Median late slowdown | Over +25% |
|---|---|---|---|
| 2014 | 31,634 | 15.1% | 27.4% |
| 2015 | 26,306 | 7.6% | 9.9% |
| 2016 | 26,496 | 11.5% | 18.3% |
| 2017 | 26,269 | 12.3% | 21.1% |
| 2021 | 15,047 | 11.9% | 19.9% |
| 2022 | 24,390 | 8.8% | 13.7% |
| 2023 | 26,111 | 5.7% | 7.5% |
| 2024 | 25,477 | 13.2% | 22.7% |
| 2013 (halted) | 16,005 | 8.8% | 13.1% |

The 2014 row has 31,634 runners rather than 31,655 because the multi-year table drops wheelchair entrants by bib, and `analyze.py`'s 5 km filter let 21 of them through.

**Finish-time predictor.** At each mat (5, 10, 15, 20 km, half, 25, 30, 35, 40 km) a linear model predicts log(finish / even-pace projection) from the average pace so far, the last 5 km and the first 5 km against that average, their interactions, and optionally gender and age. Missing marks are filled by straight-line interpolation. Intervals are split conformal: residuals from leave-one-year-out fits, binned by fifths of current pace, give the 2.5, 10, 50, 90 and 97.5% quantiles. Training: 176,059 finishers from 2014 to 2017 and 2021 to 2023. Holdout: 2024, never used for fitting or any choice.

Results on the 2024 holdout (25,377 finishers; `tables/model_eval.json`):

| Mat | MAE even pace (min) | MAE 2014 curve | MAE model | 80% coverage | 95% coverage | Wall Brier (base rate 0.179) |
|---|---|---|---|---|---|---|
| 5 km | 25.2 | 15.0 | 15.4 | 81.0% | 95.2% | 0.172 |
| 10 km | 23.4 | 13.5 | 12.5 | 78.6% | 94.4% | 0.171 |
| Half | 18.1 | 9.9 | 7.9 | 80.0% | 94.5% | 0.161 |
| 25 km | 15.2 | 8.4 | 6.3 | 78.6% | 93.4% | 0.142 |
| 30 km | 10.3 | 6.3 | 4.3 | 76.1% | 92.9% | 0.117 |
| 35 km | 5.1 | 3.8 | 2.5 | 74.2% | 92.1% | 0.091 |
| 40 km | 1.3 | 1.2 | 0.8 | 75.2% | 92.5% | known |

"2014 curve" is the old rule behind the split card: scale the 2014 field's median pace profile to the runner's elapsed time. The model beats it from 10 km on and loses to it at 5 km. Intervals cover close to target early and run narrow late, because 2024 faded harder than most training years (22.7% hit the wall against 17.0% in training). Full table for all nine mats in `tables/model_eval.json`.

Model choice was made by leave-one-year-out error on the training years (`tables/model_compare.csv`): even pace, the 2014 curve, the linear model and gradient-boosted trees (scikit-learn `HistGradientBoostingRegressor`). The trees were 0.6 to 4% better than the linear model; I kept the linear model because it is a few hundred coefficients that NumPy and the browser evaluate identically. Scored on 2024 after the choice was locked, the trees were again 1 to 3% better.

**Wall risk.** Logistic regression on the same features, target: 35 to 40 km pace more than 25% slower than 10 to 20 km pace. Weak early (Brier 0.172 against 0.179 for the base rate at 5 km), useful late (0.091 at 35 km). On 2024 it under-predicts for most runners and over-predicts for the few given a very high risk at the half; reliability tables are in `tables/model_eval.json`.

**Pacing types.** k-means on each runner's eight segment paces divided by their own average pace, training years only. Four types, named by shape: Even (44% of training runners), Steady fade (35%), Hill fade (13%, slowest over the Newton hills then partly recovers) and Hit the wall (7%, slowest at 35 to 40 km). The fits are stable across random seeds (adjusted Rand 0.99) and fitting one year alone puts runners in the same type 72 to 92% of the time, but the silhouette score is low (0.28), so these are slices of a continuum. The mix moves a lot by year: Even was 29% of 2014 and 65% of 2023. `predict_finish` returns the nearest type on the segments seen so far, scaled by the predicted finish; on 2024 it matched the full-race type 40% of the time at 10 km (always answering the most common type gets 39%), 53% at the half, 70% at 30 km and 81% at 35 km.

**Using the model from Python.** `pace_model.py` needs only NumPy and reads `model/pace_model.json`:

```python
from pace_model import predict_finish
predict_finish({5: 22.0, 10: 44.5, 21: 95.0}, "F", 34)
# {'median_min': 195.25, 'lo80_min': 189.19, 'hi80_min': 206.5, 'lo95_min': 185.82, 'hi95_min': 217.76,
#  'wall_risk': 0.073, 'pace_type': 'Even', 'n_train': 176059, 'model_version': '2026-10-28.1'}
```

Keys are km marks passed (21 means the half), values cumulative minutes. `model/MODEL_READY` holds the commit the model was finalized in.

## Method

- Cumulative split times (decimal minutes) at 5, 10, 20, 25, 30, 35 and 40 km and the finish. Runners are kept only if every split is present and strictly increasing.
- Segment pace is segment time divided by segment distance. The field curve is the median pace per segment.
- Late slowdown is a within-runner ratio: each runner's 35 to 40 km pace against their own 10 to 20 km pace, so each runner is their own baseline.
- Finish-time groups (sub-3:00 through over 4:30) are compared against each group's own 5 to 10 km pace.

Stack: Python, pandas, NumPy, matplotlib.

## How to run

```bash
pip install -r requirements.txt
python fetch_data.py     # downloads 2014 Boston results to data/ (git-ignored)
python analyze.py        # writes figures/ and tables/
python export_web.py     # writes tables/web_pacing.json for the site's charts

# October 2026 upgrade (raw files go to ~/data-cache/marathon-pacing-decay/, not the repo)
pip install -r requirements-train.txt
python fetch_multiyear.py   # downloads the 2013-2024 source files
python build_dataset.py     # one split table across years, tables/years.csv row counts
python multiyear.py         # tables/years_decay.csv and .json
python train_model.py       # compare, fit, write model/pace_model.json, score 2024
python test_pace_model.py   # smoke test, NumPy only
```

## Repo layout

| Path | Contents |
|---|---|
| `fetch_data.py` | Downloads the 2014 results CSV |
| `analyze.py` | Computes segment paces, writes the three figures and two tables |
| `export_web.py` | Group and 15-minute band paces and the late-slowdown histogram for the site, using the same `load()` as `analyze.py` |
| `tables/` | `segment_pace.csv` (median pace per segment), `summary.csv` (sample size, slowdown metrics), `web_pacing.json` (chart data) |
| `figures/` | Pace curve, curves by finish-time group, slowdown histogram |
| `fetch_multiyear.py`, `build_dataset.py` | Download and merge the 2013-2024 split files |
| `multiyear.py` | Per-year decay curves |
| `train_model.py` | Model comparison, fit, JSON export, 2024 evaluation |
| `pace_model.py`, `model/pace_model.json` | The model at inference time (NumPy only) |
| `assets/race-tool.js`, `assets/race-tool.css` | Browser version of the model, the holdout charts and the per-year panels |
| `tables/years.csv` | Rows per year and source, what was dropped |
| `tables/model_eval.json`, `tables/model_compare.csv` | Holdout results and the leave-one-year-out comparison |
| `index.html`, `overview/` | The GitHub Pages site |
| `writeup.md` | Short write-up |

## Limitations

Split data shows where the field slows but can't tell glycogen depletion, muscle damage, heat and a fast start apart as causes. Boston's Newton hills (about 26 to 34 km) sit on the steepest part of the curve, and the net-downhill opening makes early pace look quicker, so some of the shape belongs to the course. The headline figures are one race in one year, and the per-year table shows it was a hard one. The model covers Boston only, so on a flatter course it will predict too much fade, and it knows nothing about weather: a hot year moves the whole field at once, which is why its late-race intervals ran narrow on 2024. Before 20 km the wall risk and the pacing type are weak guesses. 2018 and 2019 are missing because the public files for those years have no splits, and 2014 has no 15 km split, so the 15 km model is trained on six years. `analyze.py` labels its figure's wall at 32 km; the table puts the steepest rise between 25 and 35 km.

## Data

Official 2014 Boston Marathon results via the public mirror [llimllib/bostonmarathon](https://github.com/llimllib/bostonmarathon). For the upgrade: 2013 from the same mirror; 2015 to 2017 from the Kaggle "Finishers Boston Marathon 2015, 2016 & 2017" files as copied in [Marc-Bouche/boston-marathon-analysis](https://github.com/Marc-Bouche/boston-marathon-analysis) (2016 checked against [rojour/boston_results](https://github.com/rojour/boston_results): every finish time matches); 2021 to 2024 from `Data/allresults.rds` in [williamsorg4/BostonMarathonTimeModel](https://github.com/williamsorg4/BostonMarathonTimeModel), one row per runner per timing point. [adrian3/Boston-Marathon-Data-Project](https://github.com/adrian3/Boston-Marathon-Data-Project) has 2018 and 2019 but every split column is NULL. Wheelchair, handcycle and duo entrants are dropped in every year. Rows per year and source are in `tables/years.csv`; none of the raw data is committed. Companion study on the same field: [The Negative-Split Myth](https://github.com/lyhjeremy/marathon-negative-split-myth).

## License

[MIT](LICENSE) © 2026 Jeremy Lee
