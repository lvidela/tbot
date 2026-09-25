"""Tests for HIGH-VOLATILITY TACTICAL MODE and the opportunity queue."""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tactical, oppqueue, edge, execute, execution_stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=[]
def t(n, ok, d=""):
    P.append(ok); print(f"  [{'PASS' if ok else 'FAIL'}] {n}" + (f": {d}" if d else ""))

print("=== TACTICAL MODE TESTS ===")
PV=55.0
def mk(**kw):
    # real pair so live cost/depth lookups work; the SIGNAL values are synthetic
    base=dict(pair="LINKUSD", key="LINKUSD", bid=10.0, ask=10.01, spread_bps=10.0,
              vol_ratio=3.0, volume_ratio=5.0, mom_4h=0.03, mom_12h=0.08,
              pos_in_range=0.99, rel_strength=0.05, daily_vol=0.06, usd_vol_24h=2e7)
    base.update(kw)
    c=dict(volatility_expansion=base["vol_ratio"]>=tactical.VOL_EXPANSION_MIN,
           volume_confirmation=base["volume_ratio"]>=tactical.VOLUME_MIN,
           momentum_continuation=base["mom_4h"]>=tactical.MOMENTUM_MIN and base["mom_12h"]>0,
           breakout_confirmed=base["pos_in_range"]>=0.95 and base["mom_4h"]>0,
           relative_strength=base["rel_strength"]>=tactical.REL_STRENGTH_MIN,
           spread_acceptable=base["spread_bps"]<=tactical.MAX_SPREAD_BPS)
    base["conditions"]=c
    base["confluence"]=sum(1 for k,v in c.items() if v and k!="spread_acceptable")
    return base

# 1 volatility alone is NOT an edge
a=mk(volume_ratio=1.0, mom_4h=0.0, mom_12h=0.0, pos_in_range=0.5, rel_strength=0.0)
e=tactical.evaluate(a,PV)
t("volatility ALONE does not qualify", not e["qualifies"], f"confluence {e.get('confluence')} -> {e['reason'][:50]}")

# 2 spread veto
a=mk(spread_bps=80.0); e=tactical.evaluate(a,PV)
t("wide spread vetoes regardless of confluence", not e["qualifies"], e["reason"][:50])

# 3 confluence requirement -- must genuinely fall BELOW the threshold, and must be
# rejected FOR THAT REASON rather than incidentally failing the cost gate.
a=mk(volume_ratio=1.0, rel_strength=0.0, pos_in_range=0.5); e=tactical.evaluate(a,PV)
t(f"confluence < {tactical.MIN_CONFLUENCE} rejected for the right reason",
  (not e["qualifies"]) and e.get("confluence",9) < tactical.MIN_CONFLUENCE and "confluence" in e["reason"],
  f"confluence {e.get('confluence')} -> {e['reason'][:45]}")
# and confluence exactly AT the threshold is admitted to the EV stage (not pre-rejected)
a_at=mk(volume_ratio=1.0, rel_strength=0.0); e_at=tactical.evaluate(a_at,PV)
t("confluence exactly at threshold reaches the EV gate",
  e_at.get("confluence")==tactical.MIN_CONFLUENCE and "confluence" not in e_at["reason"],
  f"confluence {e_at.get('confluence')} -> {e_at['reason'][:46]}")

# 4 sizing bounds
a=mk(); e=tactical.evaluate(a,PV)
sf=e.get("size_frac",0)
t("position size within 15-30% band", tactical.SIZE_MIN<=sf<=tactical.SIZE_MAX, f"{sf:.0%} of portfolio")
t("size scales with confluence", tactical.evaluate(mk(),PV)["size_frac"] >= tactical.evaluate(mk(rel_strength=0.0),PV).get("size_frac",0))

# 5 exit thesis present and volatility-adjusted
x=e.get("exit_thesis",{})
t("exit thesis defined before entry", all(k in x for k in ("invalidation","max_loss_pct","trail_activate_pct","exhaustion","hard_exit")))
t("exit is volatility-adjusted not fixed %", abs(x["max_loss_pct"]-a["daily_vol"]*100)<0.01, f"max loss {x['max_loss_pct']}% = 1 daily sigma")
a2=mk(daily_vol=0.12); x2=tactical.evaluate(a2,PV)["exit_thesis"]
t("exit widens for a more volatile asset", x2["max_loss_pct"]>x["max_loss_pct"], f"{x['max_loss_pct']}% -> {x2['max_loss_pct']}%")
t("never average down is explicit", "never average down" in x["hard_exit"])

# 6 EV gate uses 4 legs and 3x
t("tactical EV gate requires move >= 3x cost", tactical.MOVE_TO_COST_MIN==3.0)
# THE CENTRAL TEST (registry D1). At the measured p=0.50 the gate CANNOT open at any
# volatility, because the directional term (2p-1) is exactly zero. This must be asserted
# explicitly and reported as a model property, never as "the market offered nothing".
big=tactical.evaluate(mk(daily_vol=0.40),PV)
t("at measured p=0.50 the gate is VACUOUS even at extreme sigma",
  (not big["qualifies"]) and big.get("gate_vacuous"),
  f"sigma 40%/d, move/cost {big['move_to_cost']}x, still {big['reason'][:42]}")
t("vacuous rejection is labelled honestly, not as a market finding",
  "NO MEASURED EDGE" in big["reason"] and "structurally vacuous" in big["reason"])
# And prove it is the PROBABILITY blocking it, not the plumbing: restore p>0.5 and the
# same setup qualifies. This pins exactly what would unlock live tactical trading.
_orig=tactical.success_probability
try:
    tactical.success_probability=lambda a: 0.62
    unlocked=tactical.evaluate(mk(daily_vol=0.40),PV)
    t("gate DOES open if a >0.5 continuation probability is ever demonstrated",
      unlocked["qualifies"], f"at p=0.62: move/cost {unlocked['move_to_cost']}x net {unlocked['net_pct']:+.2f}% -> {unlocked['verdict'] if 'verdict' in unlocked else unlocked['reason'][:20]}")
    t("gate still not trivially passable at p=0.62 with small sigma",
      not tactical.evaluate(mk(daily_vol=0.02),PV)["qualifies"])
finally:
    tactical.success_probability=_orig
t("success_probability restored after test", tactical.success_probability({"confluence":5})==0.50)

# 7 maker vs taker EV
mkr=edge.evaluate("LINKUSD",PV,5.0,0.60,sides=4,maker=True,regime="calm")
tkr=edge.evaluate("LINKUSD",PV,5.0,0.60,sides=4,maker=False)
t("maker cost < taker cost", mkr["total_pct"]<tkr["total_pct"], f"{mkr['total_pct']:.2f}% vs {tkr['total_pct']:.2f}%")
ok,why=edge.should_cross_spread(mkr,tkr)
t("failed post-only does NOT auto-cross", not ok, why[:60])

# 8 queue: nothing discarded, revalidation, staleness
oppqueue.enqueue("AAAUSD","vol+vol","A",magnitude=2.0)
oppqueue.enqueue("BBBUSD","breakout","B",magnitude=5.0)
p=oppqueue.pending()
t("concurrent distinct opportunities retained", len([r for r in p if r['asset'] in ('AAAUSD','BBBUSD')])==2, f"{len(p)} pending")
t("queue ranked by magnitude", p[0]["magnitude"]>=p[-1]["magnitude"], f"top {p[0]['asset']} @ {p[0]['magnitude']}")
oppqueue.enqueue("AAAUSD","vol+vol","A stronger",magnitude=9.0)
p2=[r for r in oppqueue.pending() if r["asset"]=="AAAUSD"][0]
t("duplicate merges keeping STRONGER signal", p2["magnitude"]==9.0, f"magnitude {p2['magnitude']}, seen x{p2['seen_count']}")
old=oppqueue.pending(max_age=0)
t("stale opportunities rejected by age", len(old)==0, "all expired at max_age=0")
for r in oppqueue.pending(): oppqueue.resolve(r["id"],"rejected","test cleanup")

# 9 multiple simultaneous tactical positions
tot=sum(tactical.evaluate(mk(),PV)["size_frac"] for _ in range(2))
t("two tactical positions fit alongside core", tot<=0.70, f"{tot:.0%} tactical, {1-tot:.0%} core retained")

# 9b REGISTRY D2 -- exchange-side exit enforcement
try:
    execute.place("LINKUSD","buy",0.6,"test","d2-regression",dry_run=True); ok3=False; d3="NOT refused"
except execute.Abort as ex: ok3="registry D2" in str(ex); d3=str(ex)[:56]
except Exception as ex: ok3=False; d3=f"wrong error: {ex}"
t("entry without an exchange-side stop is REFUSED", ok3, d3)
import inspect
_src=inspect.getsource(execute.place)
t("stop attaches as a Kraken conditional close", "close[ordertype]" in _src and "stop-loss" in _src)
t("policy guard runs BEFORE feasibility checks",
  _src.index("registry D2") < _src.index("insufficient"),
  "so a missing stop is never masked by a balance error")
t("deliberate core holding can opt out explicitly", "force_no_stop" in _src)

# 10 STOP
open(f"{ROOT}/STOP","w").write("t\n")
try:
    execute.place("LINKUSD","sell",1.0,"test","tactical-stop",dry_run=False); ok2=False; d="NOT blocked"
except execute.Abort as ex: ok2=True; d=str(ex)
except Exception as ex: ok2=False; d=str(ex)
os.remove(f"{ROOT}/STOP")
t("STOP blocks tactical execution", ok2, d)

print(f"\n{sum(P)}/{len(P)} tactical tests passed")
sys.exit(0 if all(P) else 1)
