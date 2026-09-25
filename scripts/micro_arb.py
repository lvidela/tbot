"""MICRO-ARBITRAGE watcher -- detection only, never trades.

All four mechanisms were measured short of their fee hurdle by 2.1x-16.3x (see
research/micro_arb/FINDINGS.md). That conclusion depends on inputs that COULD change:
a stablecoin depeg, a liquidity event widening a liquid pair's spread, or a fee-tier
change. This watcher re-tests the hurdles cheaply so the negative result stays live
evidence rather than decaying into an assumption.

It logs. It never places an order. Execution stays in execute.py behind the usual gates.
"""
import json, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "logs", "activity.jsonl")
MAKER_BPS, TAKER_BPS = 40.0, 80.0
CLIP_USD = 18.0
PEGGED = ("USDTZUSD", "USDCUSD", "DAIUSD", "PYUSDUSD", "RLUSDUSD")


def _log(**kw):
    kw = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "session_id": "bot:micro_arb", **kw}
    with open(LOG, "a") as fh:
        fh.write(json.dumps(kw) + "\n")


def scan(verbose=False):
    ap = kraken.public("AssetPairs"); tk = kraken.public("Ticker")
    alt2key = {}
    for k, v in ap.items(): alt2key.setdefault(v["altname"], k)
    hits = []

    # --- 1. spread capture: any LIQUID pair whose spread exceeds 2 maker legs?
    for k, v in ap.items():
        if v.get("status") != "online" or v.get("quote") != "ZUSD": continue
        t = tk.get(k)
        if not t: continue
        try:
            b, a = float(t["b"][0]), float(t["a"][0])
            vol = float(t["v"][1]) * float(t["p"][1]); ntr = int(t["t"][1])
            if b <= 0 or a < b: continue
        except Exception: continue
        sp = (a - b) / b * 1e4
        if sp > 2 * MAKER_BPS and vol > 1e6 and ntr > 500:
            hits.append(dict(kind="spread_capture", pair=v["altname"], edge_bps=sp,
                             hurdle_bps=2 * MAKER_BPS, usd_vol=vol))

    # --- 2. stablecoin dislocation beyond a 2-maker-leg round trip
    for p in PEGGED:
        k = alt2key.get(p) or (p if p in tk else None)
        t = tk.get(k)
        if not t: continue
        try:
            b, a = float(t["b"][0]), float(t["a"][0])
        except Exception: continue
        dev = abs((b + a) / 2 - 1.0) * 1e4
        if dev > 2 * MAKER_BPS:
            hits.append(dict(kind="stablecoin_depeg", pair=p, edge_bps=dev,
                             hurdle_bps=2 * MAKER_BPS))

    # --- 3. triangular, depth-checked (quoted price is worthless without size)
    tpath = os.path.join(ROOT, "research/micro_arb/triangles.json")
    if os.path.exists(tpath):
        for legA, legB, legC, base, q in json.load(open(tpath)):
            L = []
            for alt in (legA, legB, legC):
                kk = alt2key.get(alt)
                t = tk.get(kk)
                if not t: L = None; break
                try:
                    b, a = float(t["b"][0]), float(t["a"][0])
                    bu, au = float(t["b"][2]) * b, float(t["a"][2]) * a
                    if b <= 0 or a < b: L = None; break
                    L.append((b, a, bu, au))
                except Exception: L = None; break
            if not L: continue
            (ab, aa, abu, aau), (bb, ba, bbu, bau), (cb, ca, cbu, cau) = L
            gross = max(((1 / aa) * bb * cb - 1) * 100, ((1 / ca) / ba * ab - 1) * 100) * 100  # bps
            if min(abu, aau, bbu, bau, cbu, cau) < CLIP_USD:
                continue                                  # not executable at our size
            if gross > 3 * MAKER_BPS:
                hits.append(dict(kind="triangular", pair=f"{base}/{q}", edge_bps=gross,
                                 hurdle_bps=3 * MAKER_BPS))

    if verbose:
        print(f"micro-arb scan: {len(hits)} mechanism(s) clearing their fee hurdle")
        for h in hits:
            print(f"  {h['kind']:<18} {h['pair']:<14} edge {h['edge_bps']:.0f} bps vs hurdle {h['hurdle_bps']:.0f} bps")
        if not hits:
            print("  none -- consistent with the structural finding (all mechanisms short 2.1x-16.3x)")
    for h in hits:
        _log(event="analysis",
             summary=f"MICRO-ARB HURDLE CLEARED: {h['kind']} on {h['pair']} edge {h['edge_bps']:.0f} bps "
                     f"vs hurdle {h['hurdle_bps']:.0f} bps. DETECTION ONLY - no order placed.",
             reasoning="research/micro_arb/FINDINGS.md concluded all micro-arb mechanisms are excluded "
                       "by our 40bps/leg maker fee. This watcher exists so that conclusion stays live. "
                       "A hit requires manual validation before any execution: verify depth, re-price at "
                       "the decision instant, and confirm repeatability before risking capital. "
                       "One profitable-looking observation is NOT evidence of positive expectancy.")
    return hits


if __name__ == "__main__":
    scan(verbose=True)
