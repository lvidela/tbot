"""Minimal Kraken REST client — stdlib only.

Hard rules enforced here:
  * Only spot endpoints are reachable (api.kraken.com). Futures host is never used.
  * Withdrawal/transfer/funding endpoints are blacklisted and will raise.
  * Credentials are read from the env file and never printed.
"""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

API_URL = "https://api.kraken.com"
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "env")

# Hard Rule 3: never call these, not even to test access.
FORBIDDEN = (
    "Withdraw", "WithdrawInfo", "WithdrawStatus", "WithdrawCancel", "WithdrawMethods",
    "WithdrawAddresses", "DepositMethods", "DepositAddresses", "DepositStatus",
    "WalletTransfer", "Transfer", "AddExport", "CreateSubaccount", "AccountTransfer",
    "Earn/Allocate", "Earn/Deallocate", "Stake", "Unstake",
)


def _creds():
    key = secret = None
    with open(ENV_PATH) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if k.strip() == "KRAKEN_API_KEY":
                key = v
            elif k.strip() == "KRAKEN_API_SECRET":
                secret = v
    if not key or not secret:
        raise RuntimeError("KRAKEN_API_KEY / KRAKEN_API_SECRET missing from env file")
    return key, secret


def _request(url, data=None, headers=None, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
            req.add_header("User-Agent", "lisandro-research-agent/1.0")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            last = RuntimeError("HTTP %s: %s" % (e.code, body))
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise last
        except Exception as e:  # network blip
            last = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise
    raise last


def public(method, **params):
    url = "%s/0/public/%s" % (API_URL, method)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    r = _request(url)
    if r.get("error"):
        raise RuntimeError("Kraken public %s error: %s" % (method, r["error"]))
    return r["result"]


def private(method, **params):
    if any(f.lower() in method.lower() for f in FORBIDDEN):
        raise PermissionError("Hard Rule 3: endpoint %r is forbidden (funding/withdrawal/staking)" % method)
    key, secret = _creds()
    path = "/0/private/%s" % method
    params = dict(params)
    params["nonce"] = str(int(time.time() * 1000))
    post = urllib.parse.urlencode(params)
    sha = hashlib.sha256((params["nonce"] + post).encode()).digest()
    sig = hmac.new(base64.b64decode(secret), path.encode() + sha, hashlib.sha512)
    headers = {
        "API-Key": key,
        "API-Sign": base64.b64encode(sig.digest()).decode(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    r = _request(API_URL + path, data=post.encode(), headers=headers)
    if r.get("error"):
        raise RuntimeError("Kraken private %s error: %s" % (method, r["error"]))
    return r["result"]


def best_bid(pair):
    t = public("Ticker", pair=pair)
    k = list(t.keys())[0]
    return float(t[k]["b"][0])


if __name__ == "__main__":
    import sys
    scope, method = sys.argv[1], sys.argv[2]
    kw = dict(a.split("=", 1) for a in sys.argv[3:])
    fn = public if scope == "public" else private
    print(json.dumps(fn(method, **kw), indent=2))
