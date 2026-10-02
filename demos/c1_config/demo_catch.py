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
from guards.c1_engine_config import check_engine_config_read
from guards.verdict import Outcome

# The claim this demo makes, stated before anything runs.
# One class, two observables. The rules guard answers "did my rules take
# effect"; the engine guard answers "did the engine load its own config".
# The degraded run is the case the first guard cannot see.
CLAIM = {
    "broken":   {"naive": "green", "rules": Outcome.FAIL, "engine": Outcome.PASS},
    "correct":  {"naive": "green", "rules": Outcome.PASS, "engine": Outcome.PASS},
    "degraded": {"naive": "green", "rules": Outcome.PASS, "engine": Outcome.FAIL},
}


def main():
    common.prepare()
    rows = {}
    for name, with_config, as_user in (("broken", False, False),
                                       ("correct", True, False),
                                       ("degraded", True, True)):
        code, log_dir = common.run_suricata(name, with_config, as_user)
        rows[name] = {
            "exit_code": code,
            "alerts": common.count_alerts(log_dir / "eve.json"),
            "naive": "green" if code == 0 else "red",
            "rules": check_rules_in_effect(common.RULES, log_dir / "eve.json"),
            "engine": check_engine_config_read(log_dir / "suricata.log"),
        }

    print(f"\n{'run':9} {'exit':>4} {'alerts':>6}  naive  rules  engine")
    for name, r in rows.items():
        rv, ev = r["rules"], r["engine"]
        print(f"{name:9} {r['exit_code']:>4} {str(r['alerts']):>6}  {r['naive']:6} "
              f"{rv.outcome.value:6} {ev.outcome.value}")
        if rv.outcome is Outcome.FAIL:
            print(f"  rules:  {rv.reason}")
        if ev.outcome is Outcome.FAIL:
            print(f"  engine: {ev.reason}")

    results = {
        name: {"exit_code": r["exit_code"], "alerts": r["alerts"], "naive": r["naive"],
               "rules": r["rules"].to_dict(), "engine": r["engine"].to_dict()}
        for name, r in rows.items()
    }
    out = common.OUT / "results.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {out}")

    held = (all(r["naive"] == "green" for r in rows.values())
            and all(rows[n]["rules"].outcome is c["rules"] for n, c in CLAIM.items())
            and all(rows[n]["engine"].outcome is c["engine"] for n, c in CLAIM.items()))
    if held:
        print("DEMONSTRATED: the naive check passed all three runs.")
        print("  broken   - rules never loaded; the rules guard caught it.")
        print("  degraded - rules loaded and alerted, so the rules guard passed it;")
        print("             the engine could not read three of its own config files,")
        print("             and only the engine guard saw that.")
        print("One class, two observables: a guard answers the question it was built for,")
        print("and says nothing about the one it was not.")
        return 0
    print("NOT DEMONSTRATED: results differ from the claim above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
