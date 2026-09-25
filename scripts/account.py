"""Account valuation, per the CLAUDE.md method.

total_usd = sum over every asset held of (quantity x current best bid of that
asset's USD pair). USD cash counts at face value. Assets with no USD pair are
routed via the most liquid alternative and the route is recorded.

One implementation, used by every snapshot, so values stay comparable over time.
"""
import json
import sys
import datetime
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

USD_ASSETS = {"ZUSD", "USD"}
# Kraken balance asset code -> USD pair altname
PAIR_OVERRIDE = {"XXBT": "XBTUSD", "XETH": "ETHUSD", "XLTC": "LTCUSD", "XXRP": "XRPUSD",
                 "XDG": "XDGUSD", "USDT": "USDTUSD", "USDC": "USDCUSD"}
DUST_USD = 0.01


def value(verbose=False):
    balances = kraken.private("Balance")
    ap = kraken.public("AssetPairs")
    alt2key = {}
    for k, v in ap.items():
        alt2key.setdefault(v["altname"], k)

    lines, total, link_qty, link_bid = [], 0.0, 0.0, None
    for asset, qty_s in sorted(balances.items()):
        qty = float(qty_s)
        if qty == 0:
            continue
        if asset in USD_ASSETS:
            lines.append(dict(asset=asset, qty=qty, price=1.0, usd=qty, route="face value"))
            total += qty
            continue
        alt = PAIR_OVERRIDE.get(asset, asset + "USD")
        key = alt2key.get(alt)
        route = alt
        if key is None:
            lines.append(dict(asset=asset, qty=qty, price=None, usd=None, route="NO USD PAIR - unvalued"))
            continue
        bid = kraken.best_bid(key)
        usd = qty * bid
        total += usd
        if asset == "LINK":
            link_qty, link_bid = qty, bid
        lines.append(dict(asset=asset, qty=qty, price=bid, usd=usd, route=route))

    if verbose:
        print(f"{'asset':<8}{'quantity':>18}{'bid':>12}{'usd':>12}   route")
        for l in lines:
            p = f"{l['price']:.5f}" if l["price"] is not None else "n/a"
            u = f"{l['usd']:.4f}" if l["usd"] is not None else "n/a"
            flag = "  <- dust" if l["usd"] is not None and l["usd"] < DUST_USD else ""
            print(f"{l['asset']:<8}{l['qty']:>18.10f}{p:>12}{u:>12}   {l['route']}{flag}")
        print(f"{'TOTAL':<8}{'':>18}{'':>12}{total:>12.4f}")
    return dict(ts=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                balances={l["asset"]: l["qty"] for l in lines}, lines=lines,
                total_usd=round(total, 4), link_qty=link_qty, link_bid=link_bid)


if __name__ == "__main__":
    r = value(verbose="-v" in sys.argv)
    print(json.dumps({k: v for k, v in r.items() if k != "lines"}, indent=2))
