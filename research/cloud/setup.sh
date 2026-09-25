#!/usr/bin/env bash
# Cloud research environment setup -- paste into the cloud environment's "Setup script".
#
# ONLY for isolated cloud research containers. Never run on the live trading VM.
# - Creates the LOCAL path the repo's .claude/settings.json hook expects
#   (/home/lisandro/scripts/guard_bash.py) inside this container only.
# - Installs a shim there that runs research/cloud/guard_research.py from the checkout.
# - Touches nothing on the live VM, copies no credentials and no live configuration.
# - Idempotent: safe to run any number of times.
set -euo pipefail

SHIM_DIR=/home/lisandro/scripts
SHIM=$SHIM_DIR/guard_bash.py

# Refuse to run on the live VM: the real guard there is a different file; never clobber it.
if [ -f "$SHIM" ] && ! grep -q "Cloud-container shim" "$SHIM"; then
  echo "setup: $SHIM exists and is not the cloud shim -- refusing to overwrite" >&2
  exit 1
fi

mkdir -p "$SHIM_DIR"
cat > "$SHIM.tmp" <<'PY'
"""Cloud-container shim installed at /home/lisandro/scripts/guard_bash.py.

ONLY for isolated cloud research containers, where the live VM's hook path does not exist.
It runs research/cloud/guard_research.py from the checked-out repo. Fail-closed: if the repo
guard cannot be found, every Bash command is denied.
"""
import json, os, runpy, sys

candidates = [os.environ.get("CLAUDE_PROJECT_DIR", ""), "/home/user/tbot", os.getcwd()]
for root in candidates:
    path = os.path.join(root, "research", "cloud", "guard_research.py")
    if root and os.path.isfile(path):
        sys.argv = [path]
        runpy.run_path(path, run_name="__main__")
        sys.exit(0)

print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse", "permissionDecision": "deny",
    "permissionDecisionReason": "cloud guard shim: research/cloud/guard_research.py not found"}}))
PY
mv "$SHIM.tmp" "$SHIM"
echo "setup: cloud guard shim installed at $SHIM"

# Run the guard's tests if the repo is already checked out (non-fatal if it is not yet).
for root in "${CLAUDE_PROJECT_DIR:-}" /home/user/tbot; do
  t="$root/research/cloud/test_guard_research.py"
  if [ -n "$root" ] && [ -f "$t" ]; then
    python3 "$t"
    break
  fi
done

# Research dependencies (best effort; the container may already have them).
python3 -m pip install -q pandas numpy scipy requests 2>/dev/null || true
