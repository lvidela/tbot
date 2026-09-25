"""PreToolUse guard for the *cloud research* environment (NOT the live trading VM).

Why this exists
---------------
`.claude/settings.json` is the live VM's settings file. Its Bash hook points at the absolute
path `/home/lisandro/scripts/guard_bash.py`, which exists only on the live machine. In an
isolated cloud research container that path is missing, so the hook errors and every Bash call
is blocked. The live settings file is researcher-protected and must not be edited from here,
so a cloud container instead installs a tiny shim at that path
(`research/cloud/guard_bash_shim.py`) that runs THIS guard.

What it blocks (the immutable experiment constraints, adapted for research):
  1. Kraken funding endpoints (withdraw / deposit / transfer / subaccounts). No capital moves.
  2. Credential exposure: referencing Kraken secrets by name, reading .env files, dumping env.
  3. Destructive Git history operations: force-push, reset --hard, rebase, filter-branch/repo,
     remote branch deletion, reflog expiry.
  4. Any access to the live trading machine (/home/lisandro paths, ssh/scp/sftp/rsync).
  5. Rewriting/deleting historical records (activity log, journal, benchmark, registry,
     findings) and removing/renaming the STOP kill switch.

What it deliberately does NOT block: public-data downloads (curl/wget/python requests), pip
installs, research on derivatives/margin/etc. (those are research variables, and this
environment holds no trading credentials at all), ordinary commits and non-force pushes.

It only ever DENIES; silence == allow.
"""
import json
import re
import sys

PROTECTED = r"(activity\.jsonl|benchmark\.json|journal\.md|REGISTRY\.md|research/findings)"

RULES = [
    (re.compile(r"\b(Withdraw\w*|DepositMethods|DepositAddresses|DepositStatus|WalletTransfer"
                r"|AccountTransfer|CreateSubaccount)\b"),
     "Kraken funding/transfer endpoint"),
    (re.compile(r"KRAKEN_API_(KEY|SECRET)|(^|[\s/'\"])\.env\b|\bprintenv\b|^\s*env\s*($|\|)"),
     "credential exposure (secrets, .env, environment dump)"),
    (re.compile(r"\bgit\b[^;|&]*\bpush\b[^;|&]*(\s-f\b|--force|\s\+\S|\s:\S|--delete|\s-d\b)"),
     "force-push or remote branch deletion"),
    (re.compile(r"\bgit\b[^;|&]*\b(reset\s+--hard|rebase|filter-branch|filter-repo"
                r"|reflog\s+expire|update-ref\s+-d)\b"),
     "destructive Git history operation"),
    (re.compile(r"/home/lisandro|\b(ssh|scp|sftp|rsync)\b"),
     "access to the live trading machine"),
    (re.compile(r"\b(rm|unlink|shred|mv|rename)\b[^;|&]*\bSTOP\b"),
     "removing or renaming the STOP kill switch"),
    (re.compile(r"(?<![>&2])>\s*\S*" + PROTECTED), "truncating a historical record"),
    (re.compile(r"\b(sed\s+-i|truncate|perl\s+-[a-zA-Z]*i)\b[^;|&]*" + PROTECTED),
     "rewriting a historical record in place"),
    (re.compile(r"\b(rm|shred|mv)\b[^;|&]*" + PROTECTED), "deleting/moving a historical record"),
    (re.compile(r"\bchattr\b"), "changing immutable flags"),
]


def check(cmd):
    for pattern, why in RULES:
        if pattern.search(cmd):
            return why
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    why = check(cmd)
    if why:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"BLOCKED by cloud research guard: {why}.",
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
