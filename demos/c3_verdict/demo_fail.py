"""Class 3 - demo_fail: three safety verdicts, and no probe ever ran.

Runs the checker against an image where the probe binary is simply not on
PATH - a Dockerfile that did not rebuild, a cached layer, a base image that
changed. Every invocation exits 127, the checker's rule turns every nonzero
into "deny", and the pipeline is handed a clean set of verdicts saying traffic
is blocked.

Exits 0 if the failure reproduced.
"""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[2]

import checker


def main():
    os.chdir(ROOT)
    shutil.rmtree(ROOT / "out" / "c3", ignore_errors=True)  # class 6: clean slate
    rel = "out/c3/unprobed/probe.jsonl"
    name = "ss-c3-demo-fail"

    checker.start_targets("ss-probe:absent", name)
    try:
        rows = [(cid, *checker.run_check(name, cid, rel)) for cid in checker.CHECKS]
    finally:
        checker.stop(name)

    print("\nWhat the pipeline sees")
    print(f"  {'check':12} {'exit':>4}  verdict")
    for cid, code, verdict in rows:
        print(f"  {cid:12} {code:>4}  {verdict}")

    record = ROOT / rel
    denied = all(v == "deny" for _, _, v in rows)
    all_127 = all(c == 127 for _, c, _ in rows)
    print(f"\n  every check reported   : {'deny' if denied else 'mixed'}")
    print(f"  probe records written  : {'none' if not record.exists() else record}")

    if denied and all_127 and not record.exists():
        print("\nREPRODUCED: three verdicts saying traffic is blocked, and the probe")
        print("never ran once. Exit 127 is 'command not found'; the checker's rule")
        print("reads it as 'the target refused'.")
        print("Run demo_catch.py to see the guard ask for the probe's own record.")
        return 0
    print("\nNOT REPRODUCED: the checker did not behave as claimed here.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
