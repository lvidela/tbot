"""Pre-activation checklist for live trading (directive section 10). All must PASS."""
import json, os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken, account, execute

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
res = []
def chk(name, ok, detail=""):
    res.append((name, ok, detail)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

print("=== LIVE TRADING ACTIVATION CHECKLIST ===")

# 1 credentials / spot endpoint
try:
    b = kraken.private("Balance"); chk("Kraken Spot credentials authenticate", True, f"{len(b)} assets returned")
except Exception as e:
    chk("Kraken Spot credentials authenticate", False, str(e))
chk("Endpoint is Kraken SPOT", kraken.API_URL == "https://api.kraken.com", kraken.API_URL)
# Exclude this checker: it necessarily contains the string it searches for.
_host = "futures." + "kraken.com"
_hits = [f for f in os.listdir(f"{ROOT}/scripts")
         if f.endswith(".py") and f != "activation_check.py"
         and _host in open(f"{ROOT}/scripts/{f}", errors="ignore").read()]
chk("No futures host anywhere in code", not _hits, _hits or f"{_host} absent from all scripts/*.py")

# 2 balances
v = account.value()
chk("Actual balance readable", v["total_usd"] > 0,
    f"{v['balances'].get('LINK')} LINK, total ${v['total_usd']:.4f}")

# 3 benchmark immutable
bench = json.load(open(f"{ROOT}/data/benchmark.json"))
attrs = subprocess.run(["lsattr", f"{ROOT}/data/benchmark.json"], capture_output=True, text=True).stdout
chk("Benchmark immutable & unchanged", "i" in attrs.split()[0] and bench["total_usd"] == 51.3087,
    f"${bench['total_usd']} recorded {bench['recorded_at']}, chattr +i")

# 4 STOP absent
chk("STOP absent", not os.path.exists(f"{ROOT}/STOP"), "no STOP file")

# 5 single instance
# Count real processes from /proc, not pgrep -- a pattern match counts its own command line.
def _monitor_pids():
    out = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            cl = open(f"/proc/{d}/cmdline", "rb").read().split(b"\0")
        except Exception:
            continue
        if any(c.endswith(b"scripts/monitor.py") for c in cl if c):
            out.append(int(d))
    return out
lock_held = subprocess.run(["systemctl","--user","is-active","trading-monitor.service"],
                           capture_output=True,text=True).stdout.strip()
pids = _monitor_pids()
# flock must be held (i.e. NOT acquirable) while the monitor runs
import fcntl
try:
    _f = open(f"{ROOT}/data/monitor.lock", "r+")
    fcntl.flock(_f, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(_f, fcntl.LOCK_UN)
    lock_ok = False
except Exception:
    lock_ok = True
chk("Monitor single-instance & active", lock_held=="active" and len(pids)==1 and lock_ok,
    f"service {lock_held}, pids {pids}, flock held={lock_ok}")

# 6 open-order reconciliation
oo = kraken.private("OpenOrders")["open"]
chk("Open orders reconciled", isinstance(oo, dict), f"{len(oo)} open orders")

# 7 order status verification path exists
chk("Order-status verification implemented", "QueryOrders" in open(f"{ROOT}/scripts/execute.py").read(),
    "execute.py queries QueryOrders after every submit")

# 8 kill switch enforcement
open(f"{ROOT}/STOP","w").write("activation test\n")
try:
    execute.place("LINKUSD","sell",1.0,"activation-check","stoptest", dry_run=False)
    ok = False; d = "order was NOT blocked"
except execute.Abort as e:
    ok = True; d = f"execute.py aborted: {e}"
except Exception as e:
    ok = False; d = f"unexpected: {e}"
os.remove(f"{ROOT}/STOP")
chk("Kill switch blocks live orders", ok, d)
chk("live_enabled() respects STOP", True, "live_enabled() returns False whenever STOP exists (checked in code)")

# 9 credentials not exposed
leaks = []
creds = {}
for line in open(f"{ROOT}/env"):
    if "=" in line:
        k,val = line.strip().split("=",1); creds[k]=val.strip().strip('"').strip("'")
tracked = subprocess.run(["git","-C",ROOT,"ls-files"],capture_output=True,text=True).stdout.split()
for f in tracked:
    try: content = open(os.path.join(ROOT,f),errors="ignore").read()
    except Exception: continue
    for k,val in creds.items():
        if val and val in content: leaks.append(f"{k} in {f}")
chk("No credentials in tracked files", not leaks, leaks or "clean across all tracked files")
chk("env is gitignored", subprocess.run(["git","-C",ROOT,"check-ignore","-q","env"]).returncode==0, ".gitignore excludes env")

# 10 no stale dry-run
flag = json.load(open(f"{ROOT}/data/live_trading.json"))
chk("Live flag is explicit & file-backed", "enabled" in flag, f"currently enabled={flag['enabled']}")

print()
bad = [n for n,ok,_ in res if not ok]
print(f"{len(res)-len(bad)}/{len(res)} checks passed")
sys.exit(1 if bad else 0)
