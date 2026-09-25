"""Cloud-container shim installed at /home/lisandro/scripts/guard_bash.py.

ONLY for isolated cloud research containers, where the live VM's hook path does not exist.
Never install this on the live trading VM (it has its own real guard at that path).

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
