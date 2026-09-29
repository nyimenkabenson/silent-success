"""Class 6 - demo_catch: the guard judges each replay as it happens.

Runs two replays carelessly (no --clean) and two correctly, and shows the
per-run verdicts. The careless pair is the point: replay 1 passes, replay 2
fails, and both exited 0, so only the guard separates them.

Writes out/c6/results.json. Exits 0 if the guard separated them as claimed.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from guards.verdict import Outcome

ROOT = Path(__file__).resolve().parents[2]

# The claim, stated before anything runs.
CLAIM = {
    "careless": ["pass", "fail"],   # replay 1 clean, replay 2 inherits its events
    "correct": ["pass", "pass"],    # --clean each time
}


def replay(run_id, clean):
    cmd = [sys.executable, "demos/c6_carryover/replay.py", "--run-id", run_id]
    if clean:
        cmd.append("--clean")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode


def verdicts_for(run_id):
    d = ROOT / "out" / "c6" / run_id
    return [json.loads(p.read_text())
            for p in sorted(d.glob("verdict-*.json"), key=lambda p: int(p.stem.split("-")[1]))]


def main():
    os.chdir(ROOT)
    shutil.rmtree(ROOT / "out" / "c6", ignore_errors=True)

    exits = {}
    for run_id, clean in (("careless", False), ("correct", True)):
        exits[run_id] = [replay(run_id, clean) for _ in (1, 2)]

    rows = {run_id: verdicts_for(run_id) for run_id in CLAIM}

    print(f"\n{'run':9} {'replay':>6} {'exit':>4} {'alerts':>6}  guard")
    missing = []
    for run_id, vs in rows.items():
        by_seq = {v["sequence"]: v for v in vs}
        for i, code in enumerate(exits[run_id], start=1):
            # A replay that died before writing its verdict would otherwise
            # vanish from this table, leaving a report that looks complete
            # while a run is missing from it.
            if i not in by_seq:
                print(f"{run_id:9} {i:>6} {code:>4} {'-':>6}  NO VERDICT WRITTEN "
                      f"(see out/c6/{run_id}/replay-{i}-error.txt)")
                missing.append((run_id, i))
                continue
            v = by_seq[i]
            e = v["evidence"]
            print(f"{run_id:9} {i:>6} {code:>4} {e['alerts']:>6}  {v['outcome']}: {v['reason']}")

    results = {run_id: {"exits": exits[run_id], "verdicts": vs} for run_id, vs in rows.items()}
    out = ROOT / "out" / "c6" / "results.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {out.relative_to(ROOT)}")

    all_clean = all(c == 0 for codes in exits.values() for c in codes)
    held = (not missing and all_clean
            and all([v["outcome"] for v in rows[k]] == expected
                    for k, expected in CLAIM.items()))
    if held:
        print("DEMONSTRATED: all four replays exited 0; the guard failed only the one")
        print("that inherited a prior run's events. Each verdict is kept beside the")
        print("inputs it judged, so replay 1's pass survives replay 2.")
        return 0
    print("NOT DEMONSTRATED: results differ from the claim above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
