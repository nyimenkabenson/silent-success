"""Class 3 - demo_catch: the guard asks what the probe recorded.

Three scenarios, judged two ways: the naive checker's verdict, and the guard
reading the probe's own record.

  probed      - probe present, targets reachable and refusing as expected
  unprobed    - probe binary absent; every verdict is deny and nothing ran
  mismatched  - probe present, target accepts and never answers; the probe
                records a timeout and the checker calls it deny

The third is the class in miniature: a failure to evaluate reported as a
safety verdict. Writes out/c3/results.json. Exits 0 if the guard separated
the scenarios as claimed.
"""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
ROOT = Path(__file__).resolve().parents[2]

import checker
from guards.c3_verdict import check_verdict_traceable
from guards.verdict import Outcome

SCENARIOS = {
    "probed":     ("ss-probe:present", ["CHK-ALLOW", "CHK-REFUSED"]),
    "unprobed":   ("ss-probe:absent",  ["CHK-ALLOW", "CHK-REFUSED", "CHK-SILENT"]),
    "mismatched": ("ss-probe:present", ["CHK-SILENT"]),
}

# The claim, stated before anything runs.
CLAIM = {
    "probed":     {"CHK-ALLOW": Outcome.PASS, "CHK-REFUSED": Outcome.PASS},
    "unprobed":   {"CHK-ALLOW": Outcome.CANNOT_EVALUATE,
                   "CHK-REFUSED": Outcome.CANNOT_EVALUATE,
                   "CHK-SILENT": Outcome.CANNOT_EVALUATE},
    "mismatched": {"CHK-SILENT": Outcome.FAIL},
}


def run(scenario, image, check_ids):
    rel = f"out/c3/{scenario}/probe.jsonl"
    name = f"ss-c3-{scenario}"
    checker.start_targets(image, name)
    try:
        rows = []
        for cid in check_ids:
            code, verdict = checker.run_check(name, cid, rel)
            rows.append({"check_id": cid, "exit_code": code, "verdict": verdict,
                         "guard": check_verdict_traceable(cid, verdict, rel)})
        return rows
    finally:
        checker.stop(name)


def main():
    os.chdir(ROOT)
    shutil.rmtree(ROOT / "out" / "c3", ignore_errors=True)

    results = {}
    print(f"\n{'scenario':11} {'check':12} {'exit':>4}  {'verdict':7} guard")
    for scenario, (image, check_ids) in SCENARIOS.items():
        rows = run(scenario, image, check_ids)
        results[scenario] = rows
        for r in rows:
            g = r["guard"]
            print(f"{scenario:11} {r['check_id']:12} {r['exit_code']:>4}  "
                  f"{r['verdict']:7} {g.outcome.value}")
            if g.outcome is not Outcome.PASS:
                print(f"{'':11}   {g.reason}")

    out = ROOT / "out" / "c3" / "results.json"
    out.write_text(json.dumps(
        {s: [{"check_id": r["check_id"], "exit_code": r["exit_code"],
              "verdict": r["verdict"], "guard": r["guard"].to_dict()} for r in rows]
         for s, rows in results.items()},
        indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {out.relative_to(ROOT)}")

    held = all(r["guard"].outcome is CLAIM[s][r["check_id"]]
               for s, rows in results.items() for r in rows)
    if held:
        print("DEMONSTRATED: every check in every scenario produced a verdict the")
        print("checker was willing to report. The guard passed only the two backed")
        print("by a probe record that justifies them.")
        print("  unprobed   - deny with no record at all: the verdict was inferred")
        print("               from the probe's absence, so the guard refuses.")
        print("  mismatched - deny with a recorded timeout: the probe ran and")
        print("               learned nothing, which does not justify a deny.")
        return 0
    print("NOT DEMONSTRATED: results differ from the claim above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
