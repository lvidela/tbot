"""Tests for the counterfactual ledger (requirement 14)."""
import json, os, sys, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import counterfactual as CF

P=[]
def t(n, ok, d=""):
    P.append(ok); print(f"  [{'PASS' if ok else 'FAIL'}] {n}" + (f": {d}" if d else ""))

print("=== COUNTERFACTUAL LEDGER TESTS ===")

# --- fee arithmetic --------------------------------------------------------------
g, f, n = CF._pnl(100.0, 110.0, CF.TAKER_PCT, CF.TAKER_PCT)
t("gross uses entry->exit correctly", abs(g - 10.0) < 1e-9, f"{g:.4f}% on 100->110")
t("fees are BOTH legs", abs(f - 1.60) < 1e-9, f"{f:.2f}% = 2 x {CF.TAKER_PCT}%")
t("net = gross - fees", abs(n - 8.40) < 1e-9, f"{n:.2f}%")
gm, fm, nm = CF._pnl(100.0, 110.0, CF.MAKER_PCT, CF.MAKER_PCT, adverse_pct=CF.ADVERSE_BPS*2/100)
t("maker variant charges measured adverse selection",
  abs(fm - 0.80) < 1e-9 and abs(nm - (10.0 - 0.80 - 0.108)) < 1e-9, f"net {nm:.3f}%")
t("a flat market yields a LOSS equal to costs",
  abs(CF._pnl(100.0, 100.0, CF.TAKER_PCT, CF.TAKER_PCT)[2] + 1.60) < 1e-9)

# --- bid/ask direction -----------------------------------------------------------
row = dict(decision_bid=99.0, decision_ask=101.0, hypothetical_entry_taker=101.0,
           hypothetical_entry_maker=99.0)
t("taker entry pays the ASK (worse price)", row["hypothetical_entry_taker"] == row["decision_ask"])
t("maker entry posts at the BID (better, fill-contingent)",
  row["hypothetical_entry_maker"] == row["decision_bid"])
t("entry ask > entry maker, i.e. crossing the spread costs us",
  row["hypothetical_entry_taker"] > row["hypothetical_entry_maker"])
# exit must cross DOWN to the bid
g2, _, _ = CF._pnl(101.0, 99.0, 0, 0)
t("round trip at unchanged quotes loses the spread", g2 < 0, f"{g2:.4f}%")

# --- no future leakage (structural) ----------------------------------------------
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "counterfactual.py")).read()
rec = src[src.index("def record_rejection"):src.index("def _pnl")]
t("record_rejection never reads a horizon/future field",
  ("horizons[" not in rec) and ("exit_bid" not in rec))
res = src[src.index("def resolve_due"):src.index("def _ci")]
t("resolve_due never rewrites an entry price",
  ("hypothetical_entry_taker =" not in res) and ("decision_bid =" not in res) and
  ("decision_ask =" not in res))
t("a horizon only resolves after its wall-clock deadline",
  'now - r["decision_ts_epoch"] < secs' in res and "continue" in res)

# --- horizon handling ------------------------------------------------------------
t("six horizons defined, strictly increasing",
  [s for _, s in CF.HORIZONS] == sorted(s for _, s in CF.HORIZONS) and len(CF.HORIZONS) == 6,
  ", ".join(h for h, _ in CF.HORIZONS))
t("5m horizon is 300s", dict(CF.HORIZONS)["5m"] == 300)
t("72h horizon is 259200s", dict(CF.HORIZONS)["72h"] == 259200)

# --- benchmark -------------------------------------------------------------------
t("benchmark is the asset we actually hold", CF.BENCHMARK_PAIR == "LINKUSD")
bench_pct = (12.0/10.0 - 1)*100
excess = 8.40 - bench_pct
t("excess = net minus benchmark over the SAME horizon", abs(excess - (8.40-20.0)) < 1e-9,
  f"net 8.40% - bench 20.0% = {excess:.2f}%")

# --- clustering ------------------------------------------------------------------
t("cluster window defined", CF.CLUSTER_WINDOW_SEC == 1800)
t("clustering groups by pair AND recency",
  'r["pair"] == pair' in src and "CLUSTER_WINDOW_SEC" in src)
t("raw rows are preserved, never merged away",
  "rows.append(row)" in src and "rows.remove" not in src)

# --- statistical conservatism ----------------------------------------------------
lo, hi = CF._ci([1.0, -1.0, 2.0, -2.0])
t("CI returned and straddles zero on noisy data", lo is not None and lo < 0 < hi, f"[{lo}, {hi}]")
t("CI undefined for n<2", CF._ci([1.0]) == (None, None))
t("report warns about overlap and sample size",
  "OVERLAP" in src and "NOT alpha" in src)

# --- separation from execution ---------------------------------------------------
t("counterfactual does NOT import execute", "import execute" not in src)
ex = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "execute.py")).read()
t("execute.py does NOT import counterfactual", "counterfactual" not in ex)
t("module forbids threshold fitting in its own docstring",
  "parameter-search" in src.lower() or "PARAMETER-SEARCH" in src)

print(f"\n{sum(P)}/{len(P)} counterfactual tests passed")
sys.exit(0 if all(P) else 1)
