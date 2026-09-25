"""PreToolUse guard: enforce the experiment's IMMUTABLE constraints on every Bash command.

The permission allowlist is deliberately broad -- the researchers authorised full autonomous
operation, so normal work must never stop for approval. That makes a deterministic guard the
real boundary rather than the allowlist: it inspects the command string itself, so it still
applies to `python3 -c ...`, a heredoc, or any other spelling that a prefix-matched permission
rule would sail straight past.

It only ever DENIES. It can never grant a permission, and it cannot be used to widen anything.

Blocked (the immutable constraints, and nothing else):
  1. Withdrawals / deposits / transfers / staking / subaccounts -- the funding endpoints.
  2. Margin, leverage, borrowing, futures, shorting.
  3. Defeating the STOP kill switch.
  4. Falsifying or rewriting audit records, benchmark history, or the research registry.
  5. Exfiltrating credentials.

Reads JSON on stdin, writes a PreToolUse decision on stdout. Silence == allow.
"""
import json, re, sys

# --- 1. Kraken funding endpoints (Hard Rule 3). Never called, not even to test access. ----
FUNDING = re.compile(
    r"\b(Withdraw\w*|DepositMethods|DepositAddresses|DepositStatus|WalletTransfer"
    r"|AccountTransfer|CreateSubaccount|AddExport|Earn/(Allocate|Deallocate)"
    r"|Unstake|Stake)\b")

# --- 2. Margin / leverage / derivatives. Spot only. ---------------------------------------
# "leverage" as an AddOrder parameter; the derivatives endpoints live under /derivatives.
MARGIN = re.compile(r"(\bleverage\s*=|[\"']leverage[\"']\s*:|/derivatives/|\bOpenPositions\b)")

# --- 3. The kill switch must stay effective. Creating STOP is always fine; only removing,
#        renaming or clobbering it is blocked.
KILLSWITCH = re.compile(r"\b(rm|unlink|shred|mv|rename)\b[^;|&]*\bSTOP\b")

# --- 4. Audit records are append-only. Appends (>>) are fine; truncation and in-place
#        rewriting are not.
PROTECTED = r"(activity\.jsonl|benchmark\.json|journal\.md|REGISTRY\.md)"
TRUNCATE = re.compile(r"(?<!>)>\s*\S*" + PROTECTED)
INPLACE = re.compile(r"\b(sed\s+-i|truncate|perl\s+-[a-zA-Z]*i)\b[^;|&]*" + PROTECTED)
IMMUTABLE = re.compile(r"\bchattr\b[^;|&]*-i")          # un-pinning the benchmark
PROTECTED_FILES = re.compile(r"\b(rm|shred|mv)\b[^;|&]*" + PROTECTED)

# --- 5. Credentials never leave this machine. -------------------------------------------
EGRESS = re.compile(r"\b(curl|wget|nc|ncat|socat|telnet|ssh|scp|sftp|rsync)\b")
SECRETS = re.compile(r"KRAKEN_API_(KEY|SECRET)")

RULES = [
    (FUNDING,         "withdrawal/deposit/transfer/staking endpoint"),
    (MARGIN,          "margin, leverage or derivatives"),
    (KILLSWITCH,      "removing or renaming the STOP kill switch"),
    (TRUNCATE,        "truncating an append-only audit record"),
    (INPLACE,         "rewriting an append-only audit record in place"),
    (PROTECTED_FILES, "deleting or moving an audit/benchmark record"),
    (IMMUTABLE,       "clearing the immutable flag on a protected record"),
    (EGRESS,          "network egress tool (credentials must never leave this machine)"),
    (SECRETS,         "referencing credentials by name in a shell command"),
]


def check(cmd):
    """Return a denial reason, or None to allow."""
    for pattern, why in RULES:
        if pattern.search(cmd):
            return why
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0                                    # never fail a command on a parse error
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    why = check(cmd)
    if not why:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason":
                f"BLOCKED by the experiment's immutable constraints: {why}. "
                "This is not a permission prompt and cannot be approved -- see CLAUDE.md §2.",
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
