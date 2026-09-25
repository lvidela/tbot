"""Standing session checks: evaluate every STRATEGY.md section 5 re-evaluation trigger.

Run at each review session. Prints a verdict per trigger and exits non-zero if any fires,
so "hold" stays an actively re-tested conclusion rather than an assumption that calcified.
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

BASELINE_USD = 22.1439          # Phase 1, 2026-09-24
EDGE_PER_TRADE_NEEDED = 0.079   # % — measured 4h reversion capture, for reference


def autocorr(r, lag=1):
    n = len(r)
    m = statistics.mean(r)
    den = sum((x - m) ** 2 for x in r)
    return sum((r[i] - m) * (r[i - lag] - m) for i in range(lag, n)) / den if den else 0.0


def returns(interval, pair="LINKUSD"):
    d = kraken.public("OHLC", pair=pair, interval=interval)
    k = [x for x in d if x != "last"][0]
    c = [float(x[4]) for x in d[k]]
    return [(c[i] / c[i - 1] - 1) * 100 for i in range(1, len(c))]


def main():
    fired = []

    if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "STOP")):
        print("!!! STOP FILE PRESENT — cancel all orders, halt trading !!!")
        return 2

    # Trigger 1 — fee tier
    tv = kraken.private("TradeVolume", pair="LINKUSD")
    taker = float(tv["fees"]["LINKUSD"]["fee"])
    maker = float(tv["fees_maker"]["LINKUSD"]["fee"])
    print(f"[1] fee tier      taker {taker:.2f}%  maker {maker:.2f}%   (reopen if taker < 0.10%)")
    if taker < 0.10:
        fired.append("1: taker fee below 0.10%")

    # Trigger 2 — autocorrelation
    print("[2] autocorrelation (reopen if |ac| > 0.30 and |t| > 3)")
    for label, iv in (("daily", 1440), ("4h", 240), ("1h", 60)):
        r = returns(iv)
        ac = autocorr(r)
        t = ac * (len(r) ** 0.5)
        mabs = statistics.mean(abs(x) for x in r)
        edge = abs(ac) * mabs
        cost = 2 * taker + 0.043
        print(f"      {label:<6} ac={ac:+.4f} t={t:+.2f}  edge={edge:.4f}%  cost={cost:.3f}%  ratio={edge/cost:.3f}x")
        if abs(ac) > 0.30 and abs(t) > 3:
            fired.append(f"2: {label} autocorrelation {ac:+.3f} (t={t:+.2f})")

    # Trigger 3 — volatility regime
    rd = returns(1440)
    mabs_d = statistics.mean(abs(x) for x in rd[-30:])
    print(f"[3] volatility    mean |daily move| last 30d = {mabs_d:.2f}%   (reopen if > 8%)")
    if mabs_d > 8:
        fired.append(f"3: daily volatility {mabs_d:.2f}%")

    # Trigger 4 — account size
    import account
    v = account.value()
    pnl = v["total_usd"] - BASELINE_USD
    print(f"[4] account       total_usd ${v['total_usd']:.4f}  vs baseline ${BASELINE_USD:.4f} "
          f"= {pnl:+.4f} ({pnl/BASELINE_USD*100:+.2f}%)   (reopen if > $200)")
    if v["total_usd"] > 200:
        fired.append(f"4: account grew to ${v['total_usd']:.2f}")

    # Trigger 5 — spread
    t_ = kraken.public("Ticker", pair="LINKUSD")
    d_ = t_[list(t_)[0]]
    bid, ask = float(d_["b"][0]), float(d_["a"][0])
    bps = (ask - bid) / bid * 1e4
    print(f"[5] spread        LINKUSD {bps:.1f} bps   (reopen if > 50 bps)")
    if bps > 50:
        fired.append(f"5: spread {bps:.1f} bps")

    # Benchmark: 100% LINK means benchmark == total_usd while we hold
    print(f"[6] structural    none identified; requires a verified cost-covering opportunity")

    print()
    if fired:
        print("TRIGGERS FIRED — reopen STRATEGY.md section 2:")
        for f in fired:
            print("   *", f)
        return 1
    print("No triggers fired. Hold remains the tested conclusion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
