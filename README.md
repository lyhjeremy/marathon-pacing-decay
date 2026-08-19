# Hitting the Wall: the marathon pacing-decay curve

Design and copy follow [these standards](https://github.com/lyhjeremy/lyhjeremy/blob/main/DESIGN_STANDARDS.md).

Using per-5K splits from **31,655** finishers of the 2014 Boston Marathon, this
traces exactly where runners slow down. Pace holds flat to ~20 km, then climbs
steeply from about **30 km.** The wall. The median runner's late pace was **15%**
slower than mid-race, and **27%** slowed by more than 25%.

> **Read the story:** https://lyhjeremy.github.io/marathon-pacing-decay/
> **In depth:** https://lyhjeremy.github.io/marathon-pacing-decay/overview/

## Findings
- Pace is flat to ~20 km, drifts up to 25 km, then climbs steeply from **~30 km**.
- Median late slowdown (35–40 km vs 10–20 km pace) is **15%**; **27%** slowed >25%.
- The effect scales with finish time: sub-3h runners stay nearly flat; 4:30+ runners slow 30%+ late.
- Field median pace drifts from ~5.0 to ~6.1 min/km across the race.

## Reproduce
```bash
pip install -r requirements.txt
python fetch_data.py     # downloads 2014 Boston results to data/
python analyze.py        # writes figures/ and tables/
```

## Data
Official 2014 Boston Marathon results via [llimllib/bostonmarathon](https://github.com/llimllib/bostonmarathon).
Cumulative split times (decimal minutes) at 5/10/20/25/30/35/40 km and finish;
each segment's pace = time ÷ distance. Raw data is downloaded by `fetch_data.py`
and git-ignored. Companion study: [The Negative-Split Myth](https://github.com/lyhjeremy/marathon-negative-split-myth).

## License
[MIT](LICENSE) © 2026 Jeremy Lee
