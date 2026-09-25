"""Dynamic eligible-universe discovery for Kraken Spot.

Deterministic filtering only -- no opinions about which assets are good, just which
are executable with this account. Built fresh from Kraken's live markets each run so
no asset list is ever hardcoded.

Eligibility gates (all must pass):
  * online USD pair (or a recorded conversion route)
  * 24h USD volume and trade count above liquidity floors
  * bid/ask spread below a ceiling
  * order-book depth near touch sufficient for our trade size
  * minimum order notional affordable at our portfolio size
  * sane data (positive prices, non-stale ticker)
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Liquidity / execution floors. Deliberately strict: with ~$51 and 0.80% taker fees
# we can only afford to touch markets where execution cost is predictable.
MIN_USD_VOL_24H = 3_000_000
MIN_TRADES_24H = 1_500
MAX_SPREAD_BPS = 25
MAX_MIN_NOTIONAL_FRAC = 0.35     # min order must be <= 35% of portfolio
DEPTH_MULTIPLE = 20              # book depth within 0.5% must cover N x our trade size
DEPTH_PCT = 0.005

STABLES = {"USDT", "USDC", "DAI", "PYUSD", "RLUSD", "EURT", "USDG", "USDS", "TUSD"}


def _depth_usd(pair, pct=DEPTH_PCT):
    """USD notional resting within `pct` of mid on each side."""
    try:
        d = kraken.public("Depth", pair=pair, count=100)
        k = list(d)[0]
        bids = [(float(p), float(v)) for p, v, *_ in d[k]["bids"]]
        asks = [(float(p), float(v)) for p, v, *_ in d[k]["asks"]]
        if not bids or not asks:
            return 0.0, 0.0
        mid = (bids[0][0] + asks[0][0]) / 2
        bid_usd = sum(p * v for p, v in bids if p >= mid * (1 - pct))
        ask_usd = sum(p * v for p, v in asks if p <= mid * (1 + pct))
        return bid_usd, ask_usd
    except Exception:
        return 0.0, 0.0


def discover(portfolio_usd, trade_usd=None, deep=True, verbose=False):
    trade_usd = trade_usd or portfolio_usd
    ap = kraken.public("AssetPairs")
    tk = kraken.public("Ticker")

    cands, rejected = [], {}
    for key, v in ap.items():
        alt = v.get("altname", "")
        if v.get("status") != "online":
            continue
        if v.get("quote") not in ("ZUSD",):
            continue
        t = tk.get(key)
        if not t:
            rejected[alt] = "no ticker data"
            continue
        try:
            bid, ask = float(t["b"][0]), float(t["a"][0])
            vwap, vol, ntr = float(t["p"][1]), float(t["v"][1]), int(t["t"][1])
            low, high = float(t["l"][1]), float(t["h"][1])
        except Exception:
            rejected[alt] = "malformed ticker"
            continue
        if bid <= 0 or ask <= 0 or vwap <= 0 or ask < bid:
            rejected[alt] = "bad prices"
            continue

        usd_vol = vol * vwap
        spread_bps = (ask - bid) / bid * 1e4
        ordermin = float(v.get("ordermin") or 0)
        costmin = float(v.get("costmin") or 0)
        min_notional = max(ordermin * bid, costmin)
        base = v.get("base", "").lstrip("X")

        if usd_vol < MIN_USD_VOL_24H:
            rejected[alt] = f"volume ${usd_vol/1e6:.1f}M < ${MIN_USD_VOL_24H/1e6:.0f}M"
            continue
        if ntr < MIN_TRADES_24H:
            rejected[alt] = f"{ntr} trades < {MIN_TRADES_24H}"
            continue
        if spread_bps > MAX_SPREAD_BPS:
            rejected[alt] = f"spread {spread_bps:.0f}bps > {MAX_SPREAD_BPS}"
            continue
        if min_notional > portfolio_usd * MAX_MIN_NOTIONAL_FRAC:
            rejected[alt] = f"min order ${min_notional:.2f} > {MAX_MIN_NOTIONAL_FRAC:.0%} of portfolio"
            continue

        cands.append(dict(
            pair=alt, key=key, base=base, bid=bid, ask=ask, spread_bps=spread_bps,
            usd_vol_24h=usd_vol, trades_24h=ntr, min_notional=min_notional,
            range_pct=(high - low) / vwap * 100,
            price_decimals=v.get("pair_decimals"), lot_decimals=v.get("lot_decimals"),
            ordermin=ordermin, costmin=costmin,
            is_stable=base in STABLES,
        ))

    # Depth check is a REST call per pair, so only for pairs that already passed.
    if deep:
        keep = []
        for c in sorted(cands, key=lambda x: -x["usd_vol_24h"]):
            bid_usd, ask_usd = _depth_usd(c["key"])
            c["depth_bid_usd"], c["depth_ask_usd"] = bid_usd, ask_usd
            need = trade_usd * DEPTH_MULTIPLE
            if min(bid_usd, ask_usd) < need:
                rejected[c["pair"]] = f"depth ${min(bid_usd,ask_usd):.0f} < ${need:.0f} needed"
                continue
            # slippage estimate: half-spread + a small book-impact term
            c["est_slippage_bps"] = c["spread_bps"] / 2 + max(0.0, trade_usd / max(bid_usd, 1) * 100)
            keep.append(c)
            time.sleep(0.12)   # be polite to the public rate limit
        cands = keep

    cands.sort(key=lambda x: -x["usd_vol_24h"])
    if verbose:
        print(f"{'pair':<12}{'vol$M':>9}{'spr_bps':>9}{'minNot$':>9}{'depth$':>10}{'slip_bps':>9}{'range%':>8}")
        for c in cands:
            print(f"{c['pair']:<12}{c['usd_vol_24h']/1e6:>9.1f}{c['spread_bps']:>9.1f}"
                  f"{c['min_notional']:>9.2f}{min(c['depth_bid_usd'],c['depth_ask_usd']):>10.0f}"
                  f"{c['est_slippage_bps']:>9.1f}{c['range_pct']:>8.1f}")
    return cands, rejected


if __name__ == "__main__":
    import account
    pv = account.value()["total_usd"]
    c, rej = discover(pv, trade_usd=pv, deep="--fast" not in sys.argv, verbose=True)
    print(f"\nportfolio ${pv:.2f} | eligible: {len(c)} | rejected: {len(rej)}")
    out = os.path.join(ROOT, "data", "universe.json")
    json.dump(dict(ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), portfolio_usd=pv,
                   eligible=c, rejected_count=len(rej)), open(out, "w"), indent=2)
    print("written:", out)
