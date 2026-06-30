# Hitting the Wall: the marathon pacing-decay curve

**Question.** Where, and how badly, do marathoners slow down?

**Data.** Official 2014 Boston Marathon results (`llimllib/bostonmarathon`),
31,655 finishers with complete 5K splits (cumulative decimal minutes). Each
segment's pace = segment time ÷ segment distance (min/km).

**Results.** Median segment pace (min/km): 0–5 km 5.01, 5–10 km 5.04, 10–20 km
5.17, 20–25 km 5.35, 25–30 km 5.69, 30–35 km 6.02, 35–40 km 6.09, 40–finish 6.00.
Relative to the settled 5–10 km pace, the field is +2% by 20 km, +6% by 25 km,
+13% by 30 km, and ~+20% by 35 km — a clear inflection around 30 km. The median
runner's 35–40 km pace was 15% slower than their 10–20 km pace, and 27% slowed by
more than 25%. Slowdown scales strongly with finish time: sub-3h runners stay
nearly flat; over-4:30 runners slow 30%+.

**Interpretation.** "The wall" is a measurable bend in the pace curve near 30 km,
much gentler for fitter, even-paced runners. Boston's net-downhill opening flatters
early pace, so the true slowdown is if anything understated.

See `analyze.py` and `figures/`.
