"""
fetch_multiyear.py - download the multi-year Boston split files used by
build_dataset.py. Files go to ~/data-cache/marathon-pacing-decay/raw/, outside
the repo; none of them is committed.

Sources (all public GitHub mirrors of official B.A.A. results):
  2013, 2014  llimllib/bostonmarathon          decimal minutes, no 15 km split
  2015-2017   Marc-Bouche/boston-marathon-analysis (the Kaggle "Finishers
              Boston Marathon 2015, 2016 & 2017" files)   h:mm:ss strings
  2016        rojour/boston_results            h:mm:ss, used only as a cross-check
  2015-2019   adrian3/Boston-Marathon-Data-Project   cross-check; 2018 and 2019
              have NULL in every split column, so they add no split data
  2021-2024   williamsorg4/BostonMarathonTimeModel  Data/allresults.rds,
              one row per runner per timing point, seconds
"""
import os
import urllib.request

CACHE = os.path.expanduser("~/data-cache/marathon-pacing-decay/raw")
GH = "https://raw.githubusercontent.com"
FILES = {
    "llimllib/results_2013.csv": f"{GH}/llimllib/bostonmarathon/master/results/2013/results.csv",
    "llimllib/results_2014.csv": f"{GH}/llimllib/bostonmarathon/master/results/2014/results.csv",
    "rojour/marathon_results_2016.csv": f"{GH}/rojour/boston_results/master/marathon_results_2016.csv",
    "williamsorg4/allresults.rds": f"{GH}/williamsorg4/BostonMarathonTimeModel/HEAD/Data/allresults.rds",
}
for y in (2015, 2016, 2017):
    FILES[f"kaggle/marathon_results_{y}.csv"] = f"{GH}/Marc-Bouche/boston-marathon-analysis/HEAD/csv_files/marathon_results_{y}.csv"
for y in (2015, 2016, 2017, 2018, 2019):
    FILES[f"adrian3/results{y}.csv"] = f"{GH}/adrian3/Boston-Marathon-Data-Project/master/results{y}.csv"


def main():
    for rel, url in FILES.items():
        out = os.path.join(CACHE, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            print(f"have  {rel}")
            continue
        print(f"get   {url}")
        urllib.request.urlretrieve(url, out)
        print(f"      {os.path.getsize(out):,} bytes")


if __name__ == "__main__":
    main()
