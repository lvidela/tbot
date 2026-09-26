"""Tests for P3 analyze.resolve on synthetic trades/ticks. Run: python3 research/p3_maker/test_p3.py"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location("p3a", os.path.join(HERE, "analyze.py"))
a = importlib.util.module_from_spec(s)
s.loader.exec_module(a)


def ticks(pairs):
    return {"ts": [p[0] for p in pairs], "bid": [p[1] for p in pairs], "ask": [p[2] for p in pairs]}


def trades(rows):
    return {"ts": [r[0] for r in rows], "price": [r[1] for r in rows], "side": [r[2] for r in rows]}


ORDER = {"id": "X-1", "pair": "X", "t0": 1000.0, "bid": 100.0, "ask": 100.2, "regime": "calm", "vol_ratio": 1.0,
         "quintile": 1}


def test_strict_and_touch_fills_and_adverse_markout():
    tk = ticks([(1000 + 20 * i, 99.5, 99.7) for i in range(200)])   # mid 99.6 after placement
    tr = trades([(1010, 100.2, "s"), (1020, 100.0, "s"), (1100, 99.9, "s"), (1200, 100.3, "b")])
    r = a.resolve(ORDER, tr, tk)
    assert r["bid_touch_fill_s"] == 20 and r["bid_strict_fill_s"] == 100
    assert r["ask_strict_fill_s"] == 200 and r["ask_touch_fill_s"] == 200
    # bid filled at 100, mid later 99.6 -> adverse -40 bps; ask filled at 100.2, mid 99.6 -> favourable
    assert abs(r["bid_strict_markout_60_bps"] - (-40.0)) < 1e-9
    assert r["ask_strict_markout_60_bps"] > 0


def test_no_fill_outside_window_and_trades_before_t0_ignored():
    tk = ticks([(1000 + 20 * i, 100.0, 100.2) for i in range(200)])
    tr = trades([(900, 99.0, "s"), (1000 + 1801, 99.0, "s")])
    r = a.resolve(ORDER, tr, tk)
    assert r["bid_strict_fill_s"] is None and r["bid_touch_fill_s"] is None


def test_touch_by_wrong_side_is_not_a_fill():
    tk = ticks([(1000 + 20 * i, 100.0, 100.2) for i in range(200)])
    tr = trades([(1010, 100.0, "b")])            # buyer lifting at 100.0 cannot fill a resting bid
    r = a.resolve(ORDER, tr, tk)
    assert r["bid_touch_fill_s"] is None


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
