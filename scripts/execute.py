"""Deterministic order execution with the full CLAUDE.md section 14 safety sequence.

This is the ONLY code path that may place an order. The monitor never calls it
autonomously -- a human-or-Claude decision must invoke it -- so a monitor bug or a
Claude failure cannot produce uncontrolled trading.

Sequence per order: STOP -> reconcile -> balance -> pair -> minimum -> precision ->
cost estimate -> client order id -> place -> verify status -> reconcile -> log.
"""
import json, os, sys, time, datetime, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken, account

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "logs", "activity.jsonl")
LIVE_FLAG = os.path.join(ROOT, "data", "live_trading.json")
TAKER = 0.0080


def live_enabled():
    """Live trading is an explicit, auditable file-backed state -- not a function default."""
    try:
        return bool(json.load(open(LIVE_FLAG)).get("enabled")) and not os.path.exists(
            os.path.join(ROOT, "STOP"))
    except Exception:
        return False


def log(session_id, **kw):
    kw = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "session_id": session_id, **kw}
    with open(LOG, "a") as fh:
        fh.write(json.dumps(kw) + "\n")


class Abort(Exception):
    pass


def stop_check(session_id, where):
    if os.path.exists(os.path.join(ROOT, "STOP")):
        log(session_id, event="kill_switch", summary=f"STOP file present at {where}; order aborted.")
        raise Abort("STOP file present")


def userref(tag):
    """Deterministic 32-bit client order id, so a retry maps to its original order."""
    return int(hashlib.sha256(tag.encode()).hexdigest()[:8], 16) % (2**31)


def place(pair, side, volume, session_id, tag, ordertype="market", price=None, dry_run=None,
          post_only=False, stop_loss_price=None, force_no_stop=False,
          trailing_stop_pct=None, take_profit_price=None):
    """dry_run=None (the normal case) resolves from the live-trading flag file.
    Pass dry_run=True explicitly to force a simulation regardless of the flag."""
    if dry_run is None:
        dry_run = not live_enabled()
    stop_check(session_id, "pre-order")

    # --- policy guard BEFORE feasibility checks ------------------------------
    # Registry D2: entering a position with no protective exit is the failure mode where
    # "exit on invalidation" silently depends on a session happening to run. Refuse on
    # policy first, so this is never masked by an unrelated balance or minimum error.
    if (stop_loss_price is None and trailing_stop_pct is None
            and side == "buy" and not force_no_stop):
        raise Abort("refusing to open a position with no exchange-side stop (registry D2); "
                    "pass stop_loss_price= or trailing_stop_pct=, or force_no_stop=True "
                    "for a deliberate core holding")

    # --- reconcile against Kraken ground truth -------------------------------
    bal = kraken.private("Balance")
    open_orders = kraken.private("OpenOrders")["open"]
    ref = userref(tag)
    for oid, o in open_orders.items():
        if int(o.get("userref") or 0) == ref:
            raise Abort(f"an order with userref {ref} is already open ({oid}); refusing to duplicate")

    ap = kraken.public("AssetPairs", pair=pair)
    key = list(ap)[0]
    spec = ap[key]
    if spec.get("status") != "online":
        raise Abort(f"pair {pair} status={spec.get('status')}")

    base, quote = spec["base"], spec["quote"]
    lot_dec, price_dec = int(spec["lot_decimals"]), int(spec["pair_decimals"])
    ordermin, costmin = float(spec.get("ordermin") or 0), float(spec.get("costmin") or 0)

    bid = kraken.best_bid(key)
    volume = float(("%." + str(lot_dec) + "f") % volume)      # precision
    notional = volume * bid

    # --- balance sufficiency --------------------------------------------------
    if side == "sell":
        have = float(bal.get(base, 0) or 0)
        if volume > have:
            raise Abort(f"insufficient {base}: want {volume}, have {have}")
    else:
        have = float(bal.get(quote, 0) or 0)
        if notional > have:
            raise Abort(f"insufficient {quote}: need ~{notional:.4f}, have {have}")

    # --- minimums -------------------------------------------------------------
    if volume < ordermin:
        raise Abort(f"volume {volume} below ordermin {ordermin}")
    if notional < costmin:
        raise Abort(f"notional {notional:.4f} below costmin {costmin}")

    # --- expected cost --------------------------------------------------------
    t = kraken.public("Ticker", pair=key)[key]
    spread_bps = (float(t["a"][0]) - float(t["b"][0])) / bid * 1e4
    fee_rate = 0.0040 if (post_only or ordertype == "limit") else TAKER
    est_cost = notional * (fee_rate + (0 if post_only else spread_bps / 2e4))

    req = dict(pair=pair, type=side, ordertype=ordertype, volume=("%." + str(lot_dec) + "f") % volume,
               userref=str(ref))
    if price is not None:
        req["price"] = ("%." + str(price_dec) + "f") % price
    if post_only:
        # Guarantees maker fee (0.40% vs 0.80%) -- Kraken rejects the order rather than
        # letting it cross and pay taker. Trade-off: it may not fill at all.
        req["oflags"] = "post"
    if trailing_stop_pct is not None:
        # VERIFIED 2026-09-25 against the live API with validate=true.
        # Kraken's sign convention for a SELL trailing stop is a POSITIVE percentage, which
        # it renders back as "trailing stop -5.0000%". Passing "-5%" is REJECTED. This cost
        # me a false "unsupported" conclusion the first time round.
        req["close[ordertype]"] = "trailing-stop"
        req["close[price]"] = f"+{abs(float(trailing_stop_pct)):g}%"
    elif take_profit_price is not None and stop_loss_price is None:
        req["close[ordertype]"] = "take-profit"
        req["close[price]"] = ("%." + str(price_dec) + "f") % take_profit_price
    elif stop_loss_price is not None:
        # REGISTRY D2. An exit plan that lives only in our process is not an exit plan:
        # monitor.py places no orders, so "exit on invalidation" would depend on a session
        # happening to run. Kraken's conditional close attaches an EXCHANGE-SIDE stop that
        # survives this machine being down. Spot-only: it sells assets we already hold, and
        # uses no margin, leverage or borrowing.
        req["close[ordertype]"] = "stop-loss"
        req["close[price]"] = ("%." + str(price_dec) + "f") % stop_loss_price

    if dry_run:
        print(json.dumps(dict(dry_run=True, request=req, est_notional=round(notional, 4),
                              est_cost_usd=round(est_cost, 4), est_cost_pct=round(est_cost/notional*100, 3),
                              exchange_side_stop=stop_loss_price), indent=2))
        return None

    stop_check(session_id, "immediately-pre-submit")
    log(session_id, event="order_placed", summary=f"Submitting {side} {volume} {pair} ({ordertype}).",
        pair=pair, side=side, order_type=ordertype, volume=volume, price=price, txid=None,
        reasoning=f"userref={ref} tag={tag}; est cost ${est_cost:.4f} ({est_cost/notional*100:.3f}%)")
    try:
        res = kraken.private("AddOrder", **req)
    except Exception as e:
        # Ambiguous: the order may have been accepted. Never retry blindly.
        log(session_id, event="error", summary=f"AddOrder response ambiguous or failed: {e}",
            pair=pair, side=side, volume=volume,
            reasoning="Treating as POSSIBLY ACCEPTED per CLAUDE.md section 7. Reconcile OpenOrders/ClosedOrders "
                      f"for userref={ref} before any further action. No replacement order will be placed.")
        raise

    txid = (res.get("txid") or [None])[0]
    time.sleep(2)
    status = kraken.private("QueryOrders", txid=txid) if txid else {}
    st = status.get(txid, {}) if txid else {}
    after = account.value()
    log(session_id, event="order_filled" if st.get("status") == "closed" else "order_placed",
        summary=f"Order {txid} status={st.get('status')} vol_exec={st.get('vol_exec')} cost={st.get('cost')} fee={st.get('fee')}",
        pair=pair, side=side, order_type=ordertype, volume=volume, txid=txid,
        fee=float(st.get("fee") or 0), price=float(st.get("price") or 0),
        balances=after["balances"], total_usd=after["total_usd"])
    return dict(txid=txid, status=st, account=after)


if __name__ == "__main__":
    import argparse
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("pair"); ap_.add_argument("side"); ap_.add_argument("volume", type=float)
    ap_.add_argument("--tag", required=True); ap_.add_argument("--session", default="manual")
    ap_.add_argument("--live", action="store_true")
    ap_.add_argument("--dry-run", action="store_true", help="force simulation even when live is enabled")
    ap_.add_argument("--limit", type=float, default=None, help="limit price (implies limit order)")
    ap_.add_argument("--post-only", action="store_true", help="maker-only; guarantees 0.40%% fee")
    ap_.add_argument("--stop", type=float, default=None, help="exchange-side stop-loss trigger price")
    ap_.add_argument("--force-no-stop", action="store_true", help="deliberate core holding, no stop")
    ap_.add_argument("--trail", type=float, default=None, help="exchange-side trailing stop, percent")
    a = ap_.parse_args()
    try:
        dr = True if a.dry_run else (False if a.live else None)
        place(a.pair, a.side, a.volume, a.session, a.tag, dry_run=dr,
              ordertype="limit" if a.limit else "market", price=a.limit, post_only=a.post_only,
              stop_loss_price=a.stop, force_no_stop=a.force_no_stop, trailing_stop_pct=a.trail)
    except Abort as e:
        print("ABORTED:", e); sys.exit(1)
