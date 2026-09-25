"""Shadow mode: record what the strategy WOULD have done, without placing orders.

Two jobs:
  1. Paper-trade candidate strategies so they earn live capital on evidence, not argument.
  2. Generate genuinely FORWARD out-of-sample data. Every backtest here is contaminated by
     the fact that the same model chose the thresholds; shadow records are the only clean
     evidence available, because the prediction is written down before the outcome exists.

For every detected opportunity -- traded or not -- we record predicted_move,
predicted_probability, then later realized_return, MFE, MAE, time_to_peak and
time_to_invalidation. That is the calibration dataset for the expected-move model.
"""
import fcntl, json, os, sys, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHADOW = os.path.join(ROOT, "data", "shadow_trades.json")
SLOCK = os.path.join(ROOT, "data", "shadow.lock")
COST_ROUND_TRIP = 1.83      # % all-in, 4 legs maker incl. adverse selection
BENCHMARK_PAIR = "LINKUSD"  # the actual alternative: every shadow entry is funded by selling LINK


def _benchmark_bid():
    """Best bid of the asset we would have to sell to fund a shadow entry."""
    return kraken.best_bid(BENCHMARK_PAIR)


def _rw(fn):
    with open(SLOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        rows = []
        if os.path.exists(SHADOW):
            try: rows = json.load(open(SHADOW))
            except Exception: rows = []
        out, rows = fn(rows)
        tmp = SHADOW + ".tmp"
        json.dump(rows, open(tmp, "w"), indent=2)
        os.replace(tmp, SHADOW)
        return out


def open_shadow(pair, strategy, predicted_move_pct, predicted_prob, confluence,
                signals, entry_price, exit_thesis, horizon_hours=72, notional=10.0):
    """Record a hypothetical entry. No order is placed."""
    try:
        bench_entry = _benchmark_bid()
    except Exception:
        bench_entry = None

    def fn(rows):
        rid = f"{strategy}:{pair}:{int(time.time())}"
        rows.append(dict(
            id=rid, strategy=strategy, pair=pair, status="open",
            opened=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            opened_ts=time.time(), entry_price=entry_price, notional=notional,
            predicted_move_pct=predicted_move_pct, predicted_prob=predicted_prob,
            confluence=confluence, signals=signals, exit_thesis=exit_thesis,
            horizon_hours=horizon_hours,
            benchmark_pair=BENCHMARK_PAIR, benchmark_entry_bid=bench_entry,
            benchmark_backfilled=False,
            mfe_pct=0.0, mae_pct=0.0, peak_ts=None, invalidated_ts=None,
            assumed_cost_pct=COST_ROUND_TRIP))
        return (rid, rows)
    return _rw(fn)


def mark_to_market():
    """Update every open shadow position with current price; close on exit condition."""
    def fn(rows):
        closed = []
        prices = {}
        try:
            bench_now = _benchmark_bid()
        except Exception:
            bench_now = None
        for r in rows:
            if r["status"] != "open":
                continue
            p = r["pair"]
            if p not in prices:
                try: prices[p] = kraken.best_bid(p)
                except Exception: continue
            px = prices[p]
            ret = (px / r["entry_price"] - 1) * 100
            # Decision-relevant return: a shadow entry is funded by SELLING LINK, so the
            # alternative is holding LINK, not holding cash. Absolute return alone would
            # reproduce the exact non-demeaned error rejected as R1/R6.
            be = r.get("benchmark_entry_bid")
            if be and bench_now:
                bench_ret = (bench_now / be - 1) * 100
                r["benchmark_pct"] = round(bench_ret, 3)
                r["excess_pct"] = round(ret - bench_ret, 3)
            else:
                bench_ret = None
            r["mfe_pct"] = max(r["mfe_pct"], ret)
            r["mae_pct"] = min(r["mae_pct"], ret)
            if ret >= r["mfe_pct"]:
                r["peak_ts"] = time.time()
            age_h = (time.time() - r["opened_ts"]) / 3600
            stop = -abs(r["exit_thesis"].get("max_loss_pct", 99))
            reason = None
            if ret <= stop:
                reason = f"invalidation: {ret:.2f}% <= stop {stop:.2f}%"
                r["invalidated_ts"] = time.time()
            elif age_h >= r["horizon_hours"]:
                reason = f"horizon reached ({age_h:.0f}h)"
            if reason:
                r.update(status="closed", closed=datetime.datetime.now(datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"), exit_price=px,
                         realized_gross_pct=round(ret, 3),
                         realized_net_pct=round(ret - r["assumed_cost_pct"], 3),
                         realized_net_usd=round(r["notional"] * (ret - r["assumed_cost_pct"]) / 100, 4),
                         close_reason=reason,
                         hours_held=round(age_h, 1))
                if bench_ret is not None:
                    # Holding LINK costs nothing, so the rotation pays its full cost against
                    # the benchmark. This, not realized_net_pct, is the number that says
                    # whether the trade was worth doing.
                    r["realized_benchmark_pct"] = round(bench_ret, 3)
                    r["realized_excess_gross_pct"] = round(ret - bench_ret, 3)
                    r["realized_excess_net_pct"] = round(ret - bench_ret - r["assumed_cost_pct"], 3)
                    r["realized_excess_net_usd"] = round(
                        r["notional"] * (ret - bench_ret - r["assumed_cost_pct"]) / 100, 4)
                closed.append(r)
            else:
                r["current_pct"] = round(ret, 3)
                r["hours_open"] = round(age_h, 1)
        return (closed, rows)
    return _rw(fn)


def report():
    rows = []
    if os.path.exists(SHADOW):
        try: rows = json.load(open(SHADOW))
        except Exception: pass
    done = [r for r in rows if r["status"] == "closed"]
    live = [r for r in rows if r["status"] == "open"]
    print(f"=== SHADOW LEDGER ===  {len(done)} closed, {len(live)} open")
    if done:
        net = [r["realized_net_pct"] for r in done]
        wins = [x for x in net if x > 0]
        print(f"  ABSOLUTE net after {COST_ROUND_TRIP}% costs: mean {sum(net)/len(net):+.2f}%  "
              f"win rate {len(wins)/len(net):.0%}  total ${sum(r['realized_net_usd'] for r in done):+.3f}")
        ex = [r["realized_excess_net_pct"] for r in done if "realized_excess_net_pct" in r]
        if ex:
            exw = [x for x in ex if x > 0]
            print(f"  *** vs HOLDING LINK (the decision that matters): mean {sum(ex)/len(ex):+.2f}%  "
                  f"win rate {len(exw)/len(ex):.0%}  n={len(ex)}")
            print(f"      Absolute return is NOT evidence: in a market-wide rally every shadow "
                  f"entry shows a profit while still losing to the asset it was funded by.")
        print(f"  CALIBRATION: predicted vs realized")
        for r in done[-10:]:
            print(f"    {r['pair']:<10} conf{r['confluence']} predicted {r['predicted_move_pct']:+.2f}% "
                  f"-> realized {r['realized_gross_pct']:+.2f}% (MFE {r['mfe_pct']:+.2f} MAE {r['mae_pct']:+.2f}) "
                  f"net {r['realized_net_pct']:+.2f}% [{r['close_reason']}]")
        hit = sum(1 for r in done if r["realized_gross_pct"] >= r["predicted_move_pct"])
        print(f"  realized >= predicted in {hit}/{len(done)} cases")
    live_ex = [r["excess_pct"] for r in live if "excess_pct" in r]
    for r in live:
        exs = f" excess {r['excess_pct']:+.2f}%" if "excess_pct" in r else " excess n/a"
        bf = "*" if r.get("benchmark_backfilled") else ""
        print(f"  OPEN {r['pair']:<10} conf{r['confluence']} predicted {r['predicted_move_pct']:+.2f}% "
              f"now {r.get('current_pct',0):+.2f}%{exs}{bf} ({r.get('hours_open',0):.1f}h)")
    if live_ex:
        print(f"  open marks vs LINK: mean {sum(live_ex)/len(live_ex):+.2f}%  "
              f"ahead {sum(1 for x in live_ex if x > 0)}/{len(live_ex)}   "
              f"(* = benchmark entry backfilled from OHLC)")
    return dict(closed=len(done), open=len(live))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "mark":
        c = mark_to_market()
        print(f"marked to market; {len(c)} closed this run")
    report()
