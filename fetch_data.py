"""
fetch_data.py - download the Boston Marathon 2014 results used by this analysis.

Source: llimllib/bostonmarathon (public GitHub mirror of official results).
The 2014 file includes per-runner 5K split columns and the half-marathon split,
which is what this study needs. Data is saved to ./data/ (git-ignored).
"""
import os
import urllib.request

URL = "https://raw.githubusercontent.com/llimllib/bostonmarathon/master/results/2014/results.csv"
OUT = os.path.join(os.path.dirname(__file__), "data", "boston_2014.csv")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print(f"Downloading {URL}")
    urllib.request.urlretrieve(URL, OUT)
    print(f"Saved -> {OUT} ({os.path.getsize(OUT):,} bytes)")


if __name__ == "__main__":
    main()
