"""Tests for the cloud research guard. Run: python3 research/cloud/test_guard_research.py"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from guard_research import check

BLOCK = ["cat .env", "echo $KRAKEN_API_SECRET", "git push --force origin x", "git push -f",
         "git push origin :main", "git reset --hard HEAD~1", "git rebase main", "ssh user@host",
         "ls /home/lisandro", "rm STOP", "mv STOP x", "echo x > logs/activity.jsonl",
         "sed -i s/a/b/ logs/journal.md", "rm research/findings/foo.md",
         "git rm research/REGISTRY.md", "python3 -c 'Withdraw'", "printenv", "chattr -i x"]
ALLOW = ["git push -u origin claude/exciting-feynman-g2z3fc",
         "curl -s https://api.kraken.com/0/public/Ticker", "pip install pandas",
         "python3 backtest.py > out.txt 2>&1", "echo x >> logs/activity.jsonl",
         "git commit -m 'research'", "python3 -m pytest -q", "git log --oneline", "touch STOP",
         "cat research/findings/x.md", "python3 research/collect.py --derivatives funding"]


def main():
    bad = [c for c in BLOCK if not check(c)] + [c for c in ALLOW if check(c)]
    for c in bad:
        print("WRONG:", c, "->", check(c))
    print("OK" if not bad else f"{len(bad)} failures")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
