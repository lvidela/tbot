"""Tests for analyze_e1.py (synthetic; no network). Run: python3 research/e1_calibration/test_e1.py"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location("e1", os.path.join(HERE, "analyze_e1.py"))
e = importlib.util.module_from_spec(s)
s.loader.exec_module(e)


def order(i, filled, regime="calm", pair="LINKUSD", side="buy"):
    return {"ts": f"2026-10-01T{10 + i // 60:02d}:{i % 60:02d}:00Z", "pair": pair, "side": side, "post_only": True,
            "status": "closed" if filled else "canceled", "vol_exec": "0.55" if filled else "0", "cost": "7.7",
            "latency_sec": 60 if filled else None, "regime": regime, "experiment": "E1"}


def p3(t0, strict, touch, pair="LINKUSD"):
    return {"id": str(t0), "pair": pair, "t0": t0, "max_tick_gap_s": 30,
            "bid_strict_fill_s": 10 if strict else None, "bid_touch_fill_s": 10 if touch else None,
            "bid_strict_markout_300_bps": -5.0 if strict else None,
            "ask_strict_fill_s": None, "ask_touch_fill_s": None, "ask_strict_markout_300_bps": None}


def test_calibrated_when_live_rate_inside_bracket():
    t = e.ts_of("2026-10-01T10:00:00Z")
    rows = [p3(t + i * 60, i % 10 < 7, i % 10 < 8) for i in range(100)]      # bracket [0.7, 0.8]
    orders = [order(i, i % 4 != 0) for i in range(40)]                         # live 0.75
    r = e.evaluate(orders, rows, markout_fn=lambda o: -4.0 if o["status"] == "closed" else None)
    assert r["calm"]["fill_calibrated"] is True and abs(r["calm"]["live_fill_5min"] - 0.75) < 1e-9
    assert r["resolution"]["Ha_ready"] and not r["resolution"]["Hb_ready"]


def test_not_calibrated_when_live_rate_far_below():
    t = e.ts_of("2026-10-01T10:00:00Z")
    rows = [p3(t + i * 60, True, True) for i in range(100)]                    # bracket [1.0, 1.0]
    orders = [order(i, i % 5 == 0) for i in range(40)]                         # live 0.2
    r = e.evaluate(orders, rows, markout_fn=lambda o: None)
    assert r["calm"]["fill_calibrated"] is False


def test_only_tagged_e1_orders_counted():
    rows = [order(0, True), {**order(1, True), "experiment": None}, {**order(2, True), "pair": "ETHUSD"}]
    import json, tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(rows, f)
    assert len(e.live_orders(f.name)) == 1


if __name__ == "__main__":
    tests = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    for n, f in tests:
        f()
        print("ok ", n)
    print(f"{len(tests)}/{len(tests)} passed")
