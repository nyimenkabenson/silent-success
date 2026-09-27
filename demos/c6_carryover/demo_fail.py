"""Class 6 - demo_fail: two correct replays, and the second one lies.

Nothing is misconfigured here. The command is right, the rules load, the
pcap is the same. The only mistake is running it twice without clearing the
output first - which is what the replay protocol has always required, and
what nothing in the tool's own output would tell you was skipped.

Exits 0 if the carryover reproduced.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "c6" / "careless"


def replay():
    proc = subprocess.run(
        [sys.executable, "demos/c6_carryover/replay.py", "--run-id", "careless"],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout


def alerts_in(path):
    return sum(1 for l in Path(path).read_text().splitlines()
               if l.strip() and json.loads(l).get("event_type") == "alert")


def main():
    os.chdir(ROOT)
    shutil.rmtree(ROOT / "out" / "c6", ignore_errors=True)

    print("Two replays of the same pcap, the second without clearing the output.\n")
    rows = []
    for n in (1, 2):
        code, _ = replay()
        rows.append((n, code, alerts_in(OUT / "eve.json")))

    print(f"{'replay':7} {'exit':>4} {'alerts in eve.json':>19}")
    for n, code, a in rows:
        print(f"{n:<7} {code:>4} {a:>19}")

    _, _, first = rows[0]
    _, _, second = rows[1]
    clean_exits = all(code == 0 for _, code, _ in rows)

    print(f"\n  pipeline verdict   : {'CLEAN' if clean_exits else 'NOT CLEAN'} (both replays exited 0)")
    print(f"  events from replay 1 still in the file: {first}")

    if clean_exits and second > first:
        print(f"\nREPRODUCED: replay 2 reports {second} alerts for a one-packet pcap,")
        print("because replay 1's events were never cleared. Both exited 0.")
        print("Run demo_catch.py to see the guard judge each replay as it happens.")
        return 0
    print("\nNOT REPRODUCED: the replays did not behave as claimed here.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
