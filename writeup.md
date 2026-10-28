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

Code: `fetch_data.py`, `analyze.py`. Figures in `figures/`, tables in `tables/`.
