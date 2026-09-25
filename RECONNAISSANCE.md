# Phase 0 — Reconnaissance

**Date:** 2026-09-24 (first session)
**Status:** Recon complete. **Phase 1 is BLOCKED — Kraken API credentials are rejected.**
**Orders placed this phase:** none (Phase 0 is read-only by rule).

---

## 1. Headline finding

The Kraken credentials in `env` are **rejected by Kraken spot with `EAPI:Invalid key`** on every
private endpoint. I cannot read balances, cannot confirm the starting LINK position, and cannot
trade. See §6 for the full diagnosis and what the researchers need to do.

Everything that does not depend on authentication has been completed.

---

## 2. VM

| Item | Value |
|---|---|
| Host | `trading-bot` (GCE instance, persistent disk `trading-bot`) |
| OS | Ubuntu 24.04.5 LTS, kernel 7.0.0-1011-gcp, x86_64 |
| CPU / RAM | 2 vCPU / 3.8 GiB (no swap) |
| Disk | 67 GB root, 2.8 GB used (5%) — ample |
| Egress IP | `8.231.48.117` (relevant: Kraken API keys can be IP-whitelisted) |
| Network | Outbound HTTPS to `api.kraken.com` confirmed working |

**Runtimes present:** Python 3.12.3, Node v24.21.0, npm 11.19.0, systemd 255, jq 1.7, curl 8.5.0.
**Absent:** `pip` (no `ensurepip`), Docker, sqlite3, tmux, crontab. `git` was absent — **I installed it**
(`apt-get install git`, now 2.43.0) because the session routine requires commits.

**Privileges:** passwordless `sudo` is available.
**systemd user services:** usable — `systemctl --user` is running and `Linger=yes` is set for this
user, so a user service will survive logout and reboot. No user units exist yet.

**Session launcher:** I could not find the job that launches my sessions — no crontab, no systemd
timer, and no unit matching claude/agent/trading. It is presumably external to this VM (or owned by
user `yonoboton`, whose session is also on this box). Nothing was touched either way.

**Deliberate choice: no pip.** `pip` is missing and rather than bootstrapping it I wrote the Kraken
client against the Python **standard library only** (`hmac`, `hashlib`, `base64`, `urllib`). Zero
dependencies means nothing to break on reboot and no supply-chain surface.

---

## 3. Repository

The working directory `/home/lisandro` was effectively empty: `CLAUDE.md` and `env` only, and **not**
a git repository. Nothing pre-existing was overwritten.

Created this session:

```
.gitignore          excludes env/.env and key material
.env -> env         symlink; CLAUDE.md specifies .env, the file shipped as env.
                    A symlink satisfies both without a second copy of the secret on disk.
scripts/kraken.py   stdlib-only Kraken REST client (see §5)
logs/               activity.jsonl, journal.md
data/ strategies/ metrics/ researcher/
RECONNAISSANCE.md   this file
```

`env` permissions tightened to `600`. Git repo initialized; `.gitignore` verified to exclude the
credential file **before** the first commit, and staged files were checked for secrets.

---

## 4. Kraken — what works and what does not

### Public endpoints: fully working

`Time`, `Ticker`, `AssetPairs`, `Depth`, `OHLC` all respond normally.

**LINK/USD at 2026-09-24 11:34 UTC**

| Metric | Value |
|---|---|
| Best bid / ask | 12.22376 / 12.22906 |
| Spread | 0.0053 (**4.3 bps**) |
| 24h VWAP / low / high | 12.4394 / 12.0608 / 12.7719 |
| 24h volume / trades | 681,406 LINK / 11,287 trades |

LINK is liquid; a $22 order is noise against 681k LINK of daily volume, so market impact is nil and
the 4.3 bps spread is the only real execution cost besides fees.

**Order constraints for candidate pairs**

> **CORRECTED 2026-09-24 session 2:** the "min notional" column below understated BTC/ETH/SOL by quoting
> `costmin` ($0.50) rather than the true binding constraint `max(ordermin × price, costmin)`. Real values:
> XBTUSD **$4.17**, XETHZUSD **$2.65**, SOLUSD **$6.79**. See `STRATEGY.md` §7 for the full 617-pair survey.

| Pair | ordermin | min notional @ spot | price decimals | tick |
|---|---|---|---|---|
| LINKUSD | 0.55 LINK | **~$6.72** | 5 | 0.00001 |
| XXBTZUSD | 0.00005 BTC | ~$0.50 | 1 | 0.1 |
| XETHZUSD | 0.001 ETH | ~$0.50 | 2 | 0.01 |
| SOLUSD | 0.06 SOL | ~$0.50 | 2 | 0.01 |
| USDTZUSD | 5 USDT | $5.00 | 5 | 0.00001 |

All show `costmin` $0.50 and `status: online`. 622 USD pairs are online.

### Private endpoints: all rejected

`Balance`, `OpenOrders`, `TradeBalance` → `EAPI:Invalid key` (identical error each time).

### Fee tier: unknown, and not knowable yet

Kraken **no longer publishes** the fee schedule through `AssetPairs` — `fees` and `fees_maker` come
back as empty arrays for every pair I checked. The real tier requires the private `TradeVolume`
endpoint, which is blocked. **Assumption pending verification: 0.25% maker / 0.40% taker** (Kraken's
published entry tier for <$50k 30-day volume). This must be confirmed as the first action once the
credentials work, because the whole strategy hinges on it (§7).

---

## 5. Client design and hard-rule enforcement

`scripts/kraken.py` is the single choke point for all Kraken access. Rules are enforced in code, not
by my good intentions:

- **Spot only.** `API_URL` is pinned to `https://api.kraken.com`. The futures host does not appear in
  the codebase.
- **Hard Rule 3 enforced by a blacklist.** `private()` raises `PermissionError` before signing if the
  method name matches any withdrawal / deposit / transfer / staking / subaccount endpoint. Verified:
  `private WithdrawInfo` raises rather than sending a request. Nothing was ever transmitted.
- **Secrets never surface.** Credentials are parsed from `env` inside the client and never logged,
  printed, or passed on a command line. Every diagnostic in this session printed lengths, hashes, or
  masked values only — no credential value was ever rendered.
- Retries with exponential backoff on 429/5xx only; nonce is millisecond-based and monotonic.

---

## 6. Credential diagnosis

**The failure is not in my code.** I validated the HMAC-SHA512 signing routine against Kraken's own
published test vector from their API documentation:

```
computed: 4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ==
expected: 4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ==
```

Byte-identical. The signing is correct.

This is corroborated by the error string itself. Kraken distinguishes `EAPI:Invalid signature`
(key recognized, signature wrong) from `EAPI:Invalid key` (key not recognized at all). I get the
latter, consistently, on three different endpoints.

**The `env` file contains one credential pair duplicated into two names.** `FUTURES_API_KEY` and
`KRAKEN_API_KEY` are byte-identical (SHA-256 fingerprints match); likewise the two secrets. Format is
56-char key / 88-char base64 secret, which parses cleanly — no stray quotes, whitespace, or encoding
damage, and the secret base64-decodes to 66 bytes.

So the credential is *well-formed* but *not a valid spot key on this account*. Most likely causes,
in my order of confidence:

1. **The pair is a Kraken Futures credential pasted into both slots.** The duplication is the tell.
   Futures keys live on a different system and will never authenticate against `api.kraken.com`.
2. **IP whitelist mismatch.** If the key is restricted to an address other than `8.231.48.117`,
   Kraken can return `EAPI:Invalid key`. This VM's egress IP is in §2 if it needs whitelisting.
3. Key revoked, not yet activated, or belonging to a different Kraken account.

**Hard Rule 3 compliance note.** I did **not** test the futures credentials against the futures API,
and will not. Hard Rule 2 forbids futures/leverage outright, so those endpoints have no legitimate
use here regardless of what the keys unlock. Recording the fact that futures-labelled credentials are
present on this machine, as the rule requires, and leaving them alone.

**What I need from the researchers:** a Kraken **spot** API key and secret for the account holding
the LINK, with **Query Funds** + **Query/Create/Cancel Orders** permissions and **no** withdrawal
permission, whitelisted to `8.231.48.117` if IP restrictions are in use. Replacing the
`KRAKEN_API_KEY` / `KRAKEN_API_SECRET` values in `env` is sufficient — no other change is needed, and
the next session will pick them up automatically and proceed straight into Phase 1.

---

## 7. Proposed architecture

Deliberately small. The account is ~$22; complexity has a cost and buys nothing here.

- **`scripts/kraken.py`** — the only path to the exchange (§5).
- **`scripts/account.py`** *(next session)* — valuation per the CLAUDE.md method: for every asset
  held, quantity × current best bid of its USD pair; USD cash at face. Emits `balance_snapshot`
  events. One implementation, used by the bot, the session routine, and `STATE.md`, so every number
  is comparable.
- **The bot** — a single Python process under a **systemd user service** (`Restart=always`,
  `linger` already enabled so it survives reboot). Single-instance enforced by an flock on a pidfile.
  State as JSON on disk, reloaded on start. Deterministic; no LLM call. Checks for `STOP` before
  every order, and logs to `logs/activity.jsonl` with `session_id=bot:<name>`.
- **Monitoring** — `systemctl --user status` plus a heartbeat line in the activity log; each review
  session verifies liveness, single-instance, and reconciles against Kraken as ground truth.

**I will not start a bot until the strategy justifies one.** A supervised process that trades a
$22 account on a bad edge just burns capital in fees on a schedule. Manual session trading comes
first; the bot gets written when there is a rule worth automating.

---

## 8. Risks

| Risk | Assessment |
|---|---|
| **Fees dominate** | The central risk. At an assumed 0.40% taker each way plus 4.3 bps spread, a round trip costs **~0.84%** — roughly **$0.18** on $22. Twenty round trips is ~17% of the account, gone, regardless of whether the calls were right. |
| **Granularity** | LINK `ordermin` is 0.55 LINK ≈ $6.72, about 31% of the account. Position sizing is near-binary; there is no scaling in or out at this size. ~~Cheaper-minimum pairs (BTC/ETH/SOL at ~$0.50) are the workaround.~~ **CORRECTED 2026-09-24 session 2:** that was wrong — $0.50 is `costmin`, but the binding constraint is `max(ordermin × price, costmin)`, which is $4.17 for BTC and $2.65 for ETH, not $0.50. No liquid USD pair is below $1. Full survey in `STRATEGY.md` §7. |
| **Benchmark is a moving target** | The hold-LINK benchmark moves with LINK. Rotating into cash and being right about direction still loses to the benchmark if LINK rallies. Beating it requires being right about *relative* moves, not just avoiding losses. |
| **Overtrading** | 3-hour sessions create a standing temptation to act. With costs this high, the null action is usually correct, and I expect most sessions to end in no trade. |
| **Single point of failure** | One VM, one process. Mitigated by systemd restart + linger; a GCE outage is simply accepted at this stake. |
| **Credential access** | Currently blocking (§6). |

---

## 9. Recommended initial strategy

To be committed to `STRATEGY.md` once balances are readable and the real fee tier is known. The
shape, given a ~0.84% round-trip cost on a ~$22 account:

**Default to holding LINK.** The benchmark is hold-LINK, and holding costs nothing while every
deviation costs ~0.84% to enter and exit. The burden of proof sits on *trading*, not on *not trading*.

**Trade only on signals with an expected move several times the cost.** A realistic bar is a
thesis worth **≥2.5%**, i.e. ~3x the round-trip cost. Below that, noise and fees swamp the edge.

**The one structural edge worth testing at this size:** LINK's realized volatility is high (the 24h
range is 12.06–12.77, **5.9%** of price) while my costs are fixed and known. That favors a small
number of mean-reversion entries at statistical extremes of a multi-day range over any
trend-following or momentum approach, which would trade far too often to survive the fee load.

**Falsification, stated up front:** if after ~15 round trips the cumulative realized P&L net of fees
trails hold-LINK, the mean-reversion hypothesis is wrong at this account size and I revert to
holding LINK outright and report that plainly. I would rather record a clean negative result than
churn the account to look busy.

> **SUPERSEDED 2026-09-24 session 2.** This section is left intact as the record of what I proposed
> before testing it. The mean-reversion hypothesis was **tested and rejected** the same day: LINK's
> lag-1 return autocorrelation is statistically indistinguishable from zero at daily and hourly
> horizons, and the one marginal 4-hour reading implies an edge ~0.079% per trade against a round-trip
> cost of 0.36–0.84%. It never reached implementation and never traded. See `STRATEGY.md` §2.
>
> **Horizon correction:** this section was written assuming a long runway. The experiment ends
> **2026-10-15 — 21 days from this recon**, per `CLAUDE.md` line 14.

Concrete parameters need OHLC history and a confirmed fee tier, so they land in `STRATEGY.md` next
session rather than being invented now.

---

## 10. State at end of Phase 0

- Orders placed: **none**. Balances: **unknown** (auth blocked).
- Starting LINK quantity and baseline `total_usd`: **not yet recorded** — this is the Phase 1
  baseline and it requires a working credential. For reference, $22 at the observed bid of 12.22376
  is ~1.80 LINK, but this is an inference from the prompt, **not** a measurement, and must not be
  used as the baseline.
- Next session: retry auth. If it works → `TradeVolume` for the real fee tier, then Phase 1 baseline
  snapshot, then `STRATEGY.md`. If it still fails → re-report and hold.
