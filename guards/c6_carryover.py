"""Class 6 guard - carryover from a prior run.

Classes 1 and 4 judge a run from evidence inside it. Class 6 cannot: run two
in isolation is indistinguishable from a healthy run one. The failure is an
absence - of a clean slate - and absence is only visible against a before.

So the guard reads two things the wrapper recorded: the pre-run state of the
output file, and the declared number of alerts a complete replay produces.
The count alone distinguishes nothing (excess events are equally consistent
with carryover, a larger pcap, or a rule firing twice); the pre-state is what
rules carryover in or out.

The pre-state is a claim by the wrapper, which the guard cannot independently
verify after the fact. See docs/limitations.md.

Assumption the guard does not check: the declared alert count is valid only for
the specific pcap and rules the declaration was written against. The guard reads
the number, not the inputs that justify it, so replaying a different pcap or a
changed rule file produces a confident verdict against a number that no longer
applies. Whoever changes an input must change the declaration.
"""
import json
from pathlib import Path

from guards.verdict import Outcome, Verdict

GUARD = "c6.output_free_of_prior_runs"


def read_declared(path):
    lines = [l.strip() for l in Path(path).read_text().splitlines()]
    values = [l for l in lines if l and not l.startswith("#")]
    return values


def check_output_free_of_prior_runs(declared_path, pre_state_path, eve_path):
    declared_path = Path(declared_path)
    pre_state_path = Path(pre_state_path)
    eve_path = Path(eve_path)
    evidence = {"declared_file": str(declared_path), "pre_state_file": str(pre_state_path),
                "eve_file": str(eve_path)}

    def cannot(reason):
        return Verdict(GUARD, Outcome.CANNOT_EVALUATE, reason, evidence)

    # --- the declared expectation ---
    if not declared_path.is_file():
        return cannot("declaration file not found; nothing to check the count against")
    values = read_declared(declared_path)
    if len(values) != 1:
        return cannot(f"declaration file holds {len(values)} values; expected exactly 1")
    try:
        expected = int(values[0])
    except ValueError:
        return cannot(f"declared value {values[0]!r} is not a whole number")
    if expected < 1:
        return cannot("declared count is zero or negative, so a run cannot be verified")
    evidence["expected_alerts"] = expected

    # --- the recorded pre-state ---
    if not pre_state_path.is_file():
        return cannot("no pre-state record, so carryover can be neither shown nor ruled out")
    try:
        state = json.loads(pre_state_path.read_text())
    except json.JSONDecodeError:
        return cannot("pre-state record is not valid JSON")
    if "existed" not in state or not isinstance(state["existed"], bool):
        return cannot("pre-state record has no boolean 'existed' field")
    existed = state["existed"]
    evidence["pre_state_existed"] = existed
    # Carry the recorded size and digest through, so a FAIL can show the before
    # and after rather than only asserting that a precondition was violated.
    for field in ("size", "sha256"):
        if field in state:
            evidence[f"pre_state_{field}"] = state[field]

    # --- the output ---
    if not eve_path.is_file():
        return cannot("output file not found")
    alerts = 0
    for n, line in enumerate(eve_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return cannot(f"output line {n} is not valid JSON")
        if event.get("event_type") == "alert":
            alerts += 1
    evidence["alerts"] = alerts
    evidence["output_size"] = eve_path.stat().st_size

    # --- the grid ---
    if existed:
        # A violated precondition is a failure whatever the count says: an
        # appending run and a truncating run are indistinguishable from the
        # count alone, so a match here would be green for the wrong reason.
        sizes = ""
        if "size" in state:
            sizes = f"; output was {state['size']} bytes before this run, {evidence['output_size']} now"
        detail = (f"{alerts} alert(s) against {expected} declared, consistent with carryover"
                  if alerts > expected else
                  f"count matches ({alerts}) but the slate was not clean")
        detail += sizes
        return Verdict(GUARD, Outcome.FAIL,
                       f"precondition violated: output existed before the run; {detail}", evidence)
    if alerts == expected:
        return Verdict(GUARD, Outcome.PASS,
                       f"clean slate, {alerts} alert(s) as declared", evidence)
    excess = "more" if alerts > expected else "fewer"
    return Verdict(GUARD, Outcome.FAIL,
                   f"{alerts} alert(s) against {expected} declared, {excess} than expected; "
                   "the slate was clean, so this is not carryover", evidence)
