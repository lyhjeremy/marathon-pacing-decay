"""Smoke tests for pace_model.py: python3 test_pace_model.py"""
import pace_model as pm

KEYS = {"median_min", "lo80_min", "hi80_min", "lo95_min", "hi95_min", "wall_risk", "pace_type", "n_train", "model_version"}


def check(r):
    assert set(r) == KEYS, r
    assert r["lo95_min"] <= r["lo80_min"] <= r["median_min"] <= r["hi80_min"] <= r["hi95_min"], r
    assert 0 <= r["wall_risk"] <= 1, r


def main():
    cases = [({5: 22.0, 10: 44.5, 21: 95.0}, "F", 34), ({5: 22.0}, None, None), ({10: 50.0, 20: 101.0}, "M", None),
             ({5: 25, 10: 50, 15: 75.5, 20: 101, 21: 106.5, 25: 127, 30: 154, 35: 182, 40: 210}, "M", 50),
             ({21.1: 100.0, 30: 145.0}, None, 61)]
    for sp, g, a in cases:
        r = pm.predict_finish(sp, g, a)
        check(r)
        print(sp, g, a, "->", r)
    # intervals narrow as the race goes on
    w = [pm.predict_finish({k: v for k, v in cases[3][0].items() if k <= c}, "M", 50) for c in (5, 21, 35)]
    assert w[0]["hi80_min"] - w[0]["lo80_min"] > w[1]["hi80_min"] - w[1]["lo80_min"] > w[2]["hi80_min"] - w[2]["lo80_min"]
    for bad in ({7: 30.0}, {5: 30.0, 10: 25.0}, {5: 5.0}):
        try:
            pm.predict_finish(bad)
            raise AssertionError(f"accepted {bad}")
        except ValueError:
            pass
    print("ok")


if __name__ == "__main__":
    main()
