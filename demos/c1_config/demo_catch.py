"""Class 1 - demo_catch: the guard tells a working run from a silently broken one.

Runs real Suricata twice - config left out, and config passed - and judges
each run two ways: the naive check (exit code 0) and the class 1 guard (read
back how many rules actually loaded). Writes out/c1/results.json.
Exits 0 if the guard separated the runs as claimed, 1 if not.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `guards`

import common
from guards.c1_config import check_rules_in_effect
from guards.verdict import Outcome

# The claim this demo makes, stated before anything runs.
CLAIM = {
    "broken": {"naive": "green", "guard": Outcome.FAIL},
    "correct": {"naive": "green", "guard": Outcome.PASS},
}


def main():
    common.prepare()
    rows = {}
    for name, with_config in (("broken", False), ("correct", True)):
        code, log_dir = common.run_suricata(name, with_config)
        rows[name] = {
            "exit_code": code,
            "alerts": common.count_alerts(log_dir / "eve.json"),
            "naive": "green" if code == 0 else "red",
            "guard": check_rules_in_effect(common.RULES, log_dir / "eve.json"),
        }

    print(f"\n{'run':8} {'exit':>4} {'alerts':>6}  {'naive':6} guard")
    for name, r in rows.items():
        v = r["guard"]
        print(f"{name:8} {r['exit_code']:>4} {str(r['alerts']):>6}  {r['naive']:6} "
              f"{v.outcome.value}: {v.reason}")

    results = {
        name: {"exit_code": r["exit_code"], "alerts": r["alerts"],
               "naive": r["naive"], "guard": r["guard"].to_dict()}
        for name, r in rows.items()
    }
    out = common.OUT / "results.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {out}")

    held = all(rows[n]["naive"] == c["naive"] and rows[n]["guard"].outcome is c["guard"]
               for n, c in CLAIM.items())
    if held:
        print("DEMONSTRATED: the naive check passed both runs; the guard failed the broken one.")
        return 0
    print("NOT DEMONSTRATED: results differ from the claim above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
