"""Verification suite for aggressive opportunistic mode (directive TESTING section)."""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monitor, execute, edge

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=[]
def t(name, ok, d=""):
    P.append(ok); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f": {d}" if d else ""))

print("=== AGGRESSIVE MODE VERIFICATION ===")

# 5 & 6: artificial limits gone
t("6h global cooldown completely removed", not hasattr(monitor,"ESCALATION_COOLDOWN_SEC"))
t("4-session/day cap completely removed", not hasattr(monitor,"MAX_ESCALATIONS_PER_DAY"))
src=open(f"{ROOT}/scripts/monitor.py").read()
t("no global rate limit remains in code",
  "suppressed by cooldown" not in src and "suppressed by daily cap" not in src)

st=dict(fired={}, escalations=[])
# 1: unrelated events trigger immediately
a,_=monitor.should_escalate("breakout","BTCUSD",1.0,st); st["fired"]["breakout:BTCUSD"]=dict(ts=time.time(),value=1.0)
b,why=monitor.should_escalate("breakout","SOLUSD",1.0,st)
t("different asset escalates immediately (BTC then SOL)", a and b, why)

# 3: different event type, same asset
st["fired"]["vol_expansion:BTCUSD"]=dict(ts=time.time(),value=3.0)
c,why=monitor.should_escalate("rel_strength","BTCUSD",0.25,st)
t("different event type on same asset escalates", c, why)

# 4: identical persistent signal debounced
st["fired"]["breakout:LINKUSD"]=dict(ts=time.time(),value=1.0)
d,why=monitor.should_escalate("breakout","LINKUSD",1.0,st)
t("identical unchanged signal IS debounced", not d, why)

# materially stronger -> immediate
e,why=monitor.should_escalate("breakout","LINKUSD",1.6,st)
t("materially stronger signal escalates immediately", e, why)

# reversal -> immediate
st["fired"]["rel_strength:ETHUSD"]=dict(ts=time.time(),value=0.25)
f,why=monitor.should_escalate("rel_strength","ETHUSD",-0.25,st)
t("signal reversal escalates immediately", f, why)

# CHANGED 2026-09-25. This used to assert the opposite: that an unchanged signal re-fires
# once MIN_REFIRE_SEC has elapsed. That time-based escape hatch is what made AAVEUSD launch
# two identical Claude sessions 74 minutes apart, so it was removed. Elapsed time is no
# longer a reason to escalate; a change in the signal is. The "no cooldown, no cap"
# guarantee is unaffected and is still asserted above and below -- what is gone is only the
# re-firing of a signal carrying no new information.
st["fired"]["breakout:XRPUSD"]=dict(ts=time.time()-6*3600,value=1.0)
g,why=monitor.should_escalate("breakout","XRPUSD",1.0,st)
t("unchanged signal does NOT re-fire on elapsed time alone (6h later)", not g, why)
st["fired"]["breakout:XRPUSD"]=dict(ts=time.time()-6*3600,value=1.0)
g2,why2=monitor.should_escalate("breakout","XRPUSD",1.7,st)
t("but the same signal 70% stronger escalates instantly, however long it has been", g2, why2)

# 2: many assets in the same hour
st2=dict(fired={},escalations=[])
n=0
for p in ["BTCUSD","ETHUSD","SOLUSD","XRPUSD","ADAUSD","LINKUSD","AVAXUSD","SUIUSD"]:
    allowed,_=monitor.should_escalate("breakout",p,1.0,st2)
    if allowed:
        n+=1
        st2["fired"][f"breakout:{p}"]=dict(ts=time.time(),value=1.0)   # record, as escalate() does
t("many assets can escalate within the same hour", n==8, f"{n}/8 admitted back-to-back, no cap")

# 7: periodic review does not gate events
t("24h review does not block event escalation",
  "never gates" in src or "Strategic review only" in src)

# 10: fees+slippage in every decision
r=edge.evaluate("LINKUSD",50,5.0,0.70)
t("fees, spread, slippage, impact in every decision",
  all(k in r for k in ("fee_pct","spread_pct","slippage_pct","impact_pct","total_pct")),
  f"total cost {r['total_pct']:.2f}%")

# 9: does not trade merely on activity -- a weak signal must fail
weak=edge.evaluate("LINKUSD",50,1.0,0.55)
t("weak signal correctly REJECTED (no activity-for-its-own-sake)", not weak["passes"],
  f"net {weak['net_pct']:+.2f}% -> {weak['verdict']}")
strong=edge.evaluate("LINKUSD",50,6.0,0.75,maker=True)
t("strong signal correctly ACCEPTED (can act)", strong["passes"],
  f"net {strong['net_pct']:+.2f}% -> {strong['verdict']}")

# 11: STOP blocks orders
open(f"{ROOT}/STOP","w").write("test\n")
try:
    execute.place("LINKUSD","sell",1.0,"test","stop-agg",dry_run=False); ok=False; d="NOT blocked"
except execute.Abort as ex: ok=True; d=str(ex)
except Exception as ex: ok=False; d=f"unexpected {ex}"
t("STOP still blocks every order", ok, d)
t("live_enabled() False while STOP present", not execute.live_enabled())
os.remove(f"{ROOT}/STOP")
t("live trading still enabled after STOP removed", execute.live_enabled())

# 12: spot-only intact
import kraken
t("spot endpoint pinned", kraken.API_URL=="https://api.kraken.com")
blocked=0
for m in ("Withdraw","WalletTransfer","DepositAddresses","Earn/Allocate","Stake"):
    try: kraken.private(m)
    except PermissionError: blocked+=1
    except Exception: pass
t("withdrawal/transfer/staking endpoints blocked", blocked==5, f"{blocked}/5 raise before signing")

print(f"\n{sum(P)}/{len(P)} tests passed")
sys.exit(0 if all(P) else 1)
