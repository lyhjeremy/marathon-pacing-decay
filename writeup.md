# Hitting the Wall: the marathon pacing-decay curve

**Question.** Where in a marathon does the field slow down, and by how much?

**Data.** Official 2014 Boston Marathon results from the public mirror `llimllib/bostonmarathon`. 31,655 finishers have a complete, strictly increasing set of cumulative splits at 5, 10, 20, 25, 30, 35 and 40 km and the finish. Each segment's pace is its time divided by its distance, in minutes per kilometer.

**Results.** Median pace by segment (min/km): 0 to 5 km 5.01, 5 to 10 km 5.04, 10 to 20 km 5.17, 20 to 25 km 5.35, 25 to 30 km 5.69, 30 to 35 km 6.02, 35 to 40 km 6.09, 40 km to finish 6.00. Against the 5 to 10 km pace, the field is +2.4% at 10 to 20 km, +6.1% at 20 to 25 km, +12.9% at 25 to 30 km and +19.4% at 30 to 35 km. Most of the rise happens in those last two steps, so the bend sits around 30 km.

For individual runners, the median 35 to 40 km pace was 15% slower than the same runner's 10 to 20 km pace, and 27% of runners slowed by more than 25%. Split by finish time, runners under 3:00 stay close to flat and runners over 4:30 slow by 30% or more (figure `figures/02_decay_by_group.png`).

**Reading it.** The wall shows up in the field's numbers as a bend in the pace curve around 30 km, and it is much gentler for faster runners. The data shows where the slowing happens and not why.

**Limitations.** Boston's Newton hills run from about 26 to 34 km and overlap the bend. The net-downhill start flatters early pace, so the slowdown against a flat-course baseline is probably understated. One race, one year. `analyze.py` marks the wall at 32 km on figure 1; the segment table puts the steepest rise between 25 and 35 km.

Code: `fetch_data.py`, `analyze.py`. Figures in `figures/`, tables in `tables/`.
