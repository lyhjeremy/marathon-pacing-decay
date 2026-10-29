# Hitting the Wall: the marathon pacing-decay curve

Ask where the wall is and every marathoner names a different mile. One runner's handful of races is too few to find out, but a whole field's timing mats can locate it. The official 2014 Boston Marathon results (from the public `llimllib/bostonmarathon` mirror) have cumulative splits at 5, 10, 20, 25, 30, 35 and 40 km and the finish, and 31,655 finishers have a complete, strictly increasing set. Dividing each segment's time by its distance gives a pace in minutes per kilometer, and the median of those paces, segment by segment, is the shape of the field's race.

| Segment | Median pace (min/km) | vs 5 to 10 km |
|---|---|---|
| 0 to 5 km | 5.01 | -0.6% |
| 5 to 10 km | 5.04 | 0.0% |
| 10 to 20 km | 5.17 | +2.4% |
| 20 to 25 km | 5.35 | +6.1% |
| 25 to 30 km | 5.69 | +12.9% |
| 30 to 35 km | 6.02 | +19.4% |
| 35 to 40 km | 6.09 | +20.7% |
| 40 km to finish | 6.00 | +19.0% |

Most of the rise comes in the 25 to 30 and 30 to 35 km steps, so the bend in the curve sits around 30 km. Before that the field barely moves.

Looking at runners one at a time tells the same story. The median runner's 35 to 40 km pace was 15% slower than their own 10 to 20 km pace, and 27% of runners slowed by more than 25%. Split by finish time and measured against each group's own 5 to 10 km pace, runners under 3:00 end 8 to 9% slower and runners over 4:30 are 33 to 35% slower between 30 and 40 km (`figures/02_decay_by_group.png`). My own best is 2:48, in Berlin, which puts me in the group whose curve bends least; the wall in these numbers belongs mostly to the back half of the field.

All of this locates the slowing and says nothing about its cause. Boston's Newton hills run from about 26 to 34 km and overlap the bend, and the net-downhill start flatters early pace, so the slowdown against a flat-course baseline is probably understated. It is one race in one year. There is also a mismatch between figure and table: `analyze.py` marks the wall at 32 km on figure 1, while the segment table puts the steepest rise between 25 and 35 km.

## October 2026 upgrade

Everything above describes one race, and the obvious objection is that 2014 might have been an odd one. It was. I added every Boston year with public 5 km splits: 2013 and 2014 from the same mirror, 2015 to 2017 from a Kaggle copy of the official results, and 2021 to 2024 from a scraped set published with a random-forest project (williamsorg4/BostonMarathonTimeModel). 2018 and 2019 exist only without splits. That is about 200,000 finishers across eight comparable years, with wheelchair, handcycle and duo entrants removed (`tables/years.csv` has the counts).

The corner is in the same place every year, between 25 and 35 km. Its height is not. In 2014 the median late slowdown was 15.1% and 27.4% of runners slowed by more than 25%; across the other seven years those numbers ran from 5.7% and 7.5% (2023) to 13.2% and 22.7% (2024). 2014 was the hardest fade in the set. I left 2013 out of the comparison: the race was stopped at about 4:09 on the race clock, so the people who finished were the faster part of the field. The 2014 numbers earlier on this page are unchanged.

With eight years it was worth asking a forward question: from the splits a runner has at a given mat, what will they finish in? At each mat a linear model predicts how much slower than even pace the rest of the race will be, from the average pace so far, the last 5 km and the first 5 km against that average, and optionally gender and age. I trained on 2014 to 2017 and 2021 to 2023 and held 2024 out entirely. Model choices were made by leaving out one training year at a time. Gradient-boosted trees were 0.6 to 4% more accurate than the linear model; I kept the linear one because the browser and a NumPy-only Python module can run the same few hundred coefficients exactly.

On 2024, at the half, the model's typical miss was 7.9 minutes, against 18.1 for even pace and 9.9 for scaling the 2014 curve. At 5 km the 2014 curve was slightly better, 15.0 against 15.4. The 80% and 95% ranges are split conformal intervals built from the leave-one-year-out errors, so they include year-to-year swings; on 2024 they held 79 to 81% and 94 to 95% of runners through the half, then slipped to 74% and 92% at 35 km, because 2024 faded harder than most training years. The wall-risk probability barely beats the base rate before 20 km (Brier 0.172 against 0.179 at 5 km) and is useful after 30 km (0.091 at 35 km).

Clustering each runner's pace profile gave four shapes: Even, Steady fade, Hill fade (slowest over the Newton hills, partly recovering) and Hit the wall (slowest at 35 to 40 km). They are slices of a continuum rather than clean groups (silhouette 0.28), and the mix swings with the year: Even was 29% of the 2014 field and 65% of 2023. Read from early splits, the type is close to a guess: on 2024 it matched the eventual type 40% of the time at 10 km and 70% at 30 km.

The tool on the site runs all of this in the browser from `model/pace_model.json`; `pace_model.py` does the same in Python. The model knows nothing about weather and nothing about other courses, and those are its two biggest gaps.

Code: `fetch_data.py`, `analyze.py`; for the upgrade `fetch_multiyear.py`, `build_dataset.py`, `multiyear.py`, `train_model.py`, `pace_model.py`. Figures in `figures/`, tables in `tables/`.
