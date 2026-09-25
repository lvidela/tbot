"""Triangular arbitrage on Kraken Spot, priced EXECUTABLY.

Strict rules:
  * Never use mid prices. Buying pays the ASK, selling hits the BID, every leg.
  * One Ticker call snapshots the whole exchange simultaneously -- legs priced at the
    same instant, so no look-ahead and no staleness between legs.
  * Report the GROSS dislocation first (theoretical arbitrage), then subtract real fees
    (executable-after-fees), so the four-level taxonomy is explicit.
"""
import json, os, sys, statistics
sys.path.insert(0, "/home/lisandro/scripts")
import kraken

ROOT = "/home/lisandro"
TAKER, MAKER = 0.0080, 0.0040
tri = json.load(open(os.path.join(ROOT, "research/micro_arb/triangles.json")))
ap = kraken.public("AssetPairs")
alt2key = {}
for k, v in ap.items(): alt2key.setdefault(v["altname"], k)
tk = kraken.public("Ticker")            # single simultaneous snapshot

def quote(alt):
    k = alt2key.get(alt)
    if not k or k not in tk: return None
    t = tk[k]
    try:
        b, a = float(t["b"][0]), float(t["a"][0])
        bv, av = float(t["b"][2]), float(t["a"][2])
        if b <= 0 or a <= 0 or a < b: return None
        return dict(bid=b, ask=a, bidvol=bv, askvol=av, spread_bps=(a-b)/b*1e4)
    except Exception: return None

rows = []
for legA, legB, legC, base, q in tri:
    A, B, C = quote(legA), quote(legB), quote(legC)
    if not (A and B and C): continue
    # Path: USD -> base (buy legA @ ask) -> sell base for quote-ccy (sell legB @ bid)
    #       -> sell quote-ccy for USD (sell legC @ bid)
    units = 1.0 / A["ask"]
    q_ccy = units * B["bid"]
    usd_out = q_ccy * C["bid"]
    fwd = (usd_out - 1.0) * 100
    # Reverse: USD -> quote-ccy (buy legC @ ask) -> buy base (buy legB @ ask) -> sell base (sell legA @ bid)
    qc = 1.0 / C["ask"]
    u2 = qc / B["ask"]
    usd_out2 = u2 * A["bid"]
    rev = (usd_out2 - 1.0) * 100
    best = max(fwd, rev)
    rows.append(dict(tri=f"{base}/{q}", fwd=fwd, rev=rev, best=best,
                     spreads=[A["spread_bps"], B["spread_bps"], C["spread_bps"]],
                     legs=[legA, legB, legC]))

rows.sort(key=lambda r: -r["best"])
print(f"=== {len(rows)} triangles priced from one simultaneous snapshot ===")
print(f"hurdles: all-taker 2.40%, 2-maker+1-taker 1.60%, all-maker 1.20%\n")
print(f"{'triangle':<16}{'gross_best':>12}{'sum_spreads_bps':>18}{'net_all_taker':>15}{'net_all_maker':>15}")
for r in rows[:12]:
    print(f"{r['tri']:<16}{r['best']:>+12.3f}%{sum(r['spreads']):>17.0f}"
          f"{r['best']-2.40:>+14.3f}%{r['best']-1.20:>+14.3f}%")

g = [r["best"] for r in rows]
print(f"\ngross dislocation distribution across {len(g)} triangles:")
s = sorted(g)
print(f"  max {s[-1]:+.3f}%   p99 {s[int(.99*len(s))]:+.3f}%   median {statistics.median(s):+.3f}%   min {s[0]:+.3f}%")
for level, hurdle in (("theoretical (gross > 0)", 0.0), ("after all-maker fees 1.20%", 1.20),
                      ("after mixed fees 1.60%", 1.60), ("after all-taker fees 2.40%", 2.40)):
    n = sum(1 for x in g if x > hurdle)
    print(f"  triangles profitable {level:<32}: {n:>4} / {len(g)}  ({n/len(g)*100:.1f}%)")
json.dump(rows, open(os.path.join(ROOT, "research/micro_arb/tri_snapshot.json"), "w"), indent=1)
