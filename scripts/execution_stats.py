"""Measured execution statistics -- replaces assumptions about maker fills with data.

Every order records: post-only or not, whether it filled, latency, realised fee rate,
the VOLATILITY REGIME at submission, and realised adverse selection (mid drift between
submission and fill, signed so positive = the market moved against us).

The volatility split is the point. A maker fill measured in a calm market says nothing
about fill quality during the volatility expansions our signals point at, and that is
exactly where post-only execution is most likely to fail or be adversely selected.
"""
import json, os, sys, statistics, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "data", "execution_log.json")
CALM_VOL_RATIO = 1.5      # 1d move / 30d vol below this = calm regime


def _load():
    if os.path.exists(LOG):
        try: return json.load(open(LOG))
        except Exception: pass
    return []


def vol_regime(pair):
    """Current 1d move relative to 30d vol -> 'calm' or 'volatile'."""
    try:
        d = kraken.public("OHLC", pair=pair, interval=1440)
        k = [x for x in d if x != "last"][0]
        c = [float(r[4]) for r in d[k]]
        rets = [(c[i]/c[i-1]-1) for i in range(1, len(c))]
        v30 = statistics.pstdev(rets[-30:])
        v1 = abs(rets[-1])
        ratio = v1/v30 if v30 else 0
        return ("volatile" if ratio >= CALM_VOL_RATIO else "calm"), round(ratio, 2)
    except Exception:
        return "unknown", 0.0


def record(txid, pair, side, post_only, submitted_mid, status, vol_exec, requested_vol,
           fee, cost, latency_sec, regime, vol_ratio, filled_mid=None):
    rows = _load()
    adverse_bps = None
    if filled_mid and submitted_mid:
        drift = (filled_mid/submitted_mid - 1) * 1e4
        # a sell wants price up after; a buy wants price down after. Positive = against us.
        adverse_bps = round(drift if side == "sell" else -drift, 1)
    rows.append(dict(
        ts=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        txid=txid, pair=pair, side=side, post_only=post_only, status=status,
        requested_vol=requested_vol, vol_exec=vol_exec,
        fill_frac=round(float(vol_exec)/float(requested_vol), 4) if float(requested_vol) else 0,
        fee=fee, cost=cost, fee_rate_pct=round(float(fee)/float(cost)*100, 4) if float(cost) else None,
        latency_sec=latency_sec, regime=regime, vol_ratio=vol_ratio, adverse_bps=adverse_bps))
    json.dump(rows, open(LOG, "w"), indent=2)
    return rows[-1]


def summary(verbose=True):
    rows = _load()
    out = {}
    for regime in ("calm", "volatile", "unknown"):
        sub = [r for r in rows if r["post_only"] and r["regime"] == regime]
        if not sub: continue
        filled = [r for r in sub if r["fill_frac"] >= 0.999]
        adv = [r["adverse_bps"] for r in sub if r.get("adverse_bps") is not None]
        out[regime] = dict(
            n=len(sub), fill_rate=len(filled)/len(sub),
            median_latency=statistics.median([r["latency_sec"] for r in filled]) if filled else None,
            mean_fee_rate=statistics.mean([r["fee_rate_pct"] for r in filled if r["fee_rate_pct"]]) if filled else None,
            mean_adverse_bps=round(statistics.mean(adv), 1) if adv else None)
    if verbose:
        print("=== MEASURED post-only execution (real orders only) ===")
        if not out:
            print("  no post-only orders recorded yet")
        for regime, st in out.items():
            print(f"  {regime:<9} n={st['n']:<3} fill_rate={st['fill_rate']:.0%}  "
                  f"median_latency={st['median_latency']}s  fee={st['mean_fee_rate']}%  "
                  f"adverse={st['mean_adverse_bps']}bps")
        vol = out.get("volatile")
        if not vol or vol["n"] < 5:
            print(f"\n  WARNING: only {vol['n'] if vol else 0} post-only orders measured in VOLATILE")
            print("  conditions. Maker cost of 0.40%/leg is NOT yet established for the fast markets")
            print("  our signals point at. Treat maker pricing as UNPROVEN there and size accordingly.")
    return out


def maker_fill_prob(regime="volatile", default_calm=0.95, default_volatile=0.5):
    """Measured fill probability where we have data; conservative prior where we don't."""
    st = summary(verbose=False).get(regime)
    if st and st["n"] >= 5:
        return st["fill_rate"], "measured"
    return (default_calm if regime == "calm" else default_volatile), "assumed (insufficient data)"


if __name__ == "__main__":
    summary()
    for r in ("calm", "volatile"):
        p, src = maker_fill_prob(r)
        print(f"  fill probability used for {r}: {p:.0%} ({src})")
