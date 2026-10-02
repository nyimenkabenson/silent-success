"""Class 3 guard - error turned into a verdict.

A checker that reduces "the probe exited nonzero" to "traffic was denied"
cannot tell a refusal from a probe that never ran. Exit 2 and exit 127 become
the same safety verdict, and the second one is a failure to evaluate wearing
the costume of protection.

The guard judges a verdict against the probe's own record. The checker's output
is a claim about what it believes happened; the probe's record is a trace of
what did, and only a trace can distinguish "I probed and it was refused" from
"I never probed". A verdict must be traceable to an executed probe, never
inferred from its absence.

What this guard does NOT claim. The trace proves the probe ran, not that it
reached the target. A probe that ran and recorded a timeout still has no
evidence about whether the port is blocked. The claim here is narrower than
"the verdict is correct": it is "the verdict is traceable to an executed
probe, and the probe's result is one that justifies it".

The guard judges one check at a time and never aggregates. Aggregating several
checks would need a precedence rule - does a proven mismatch outrank an
unevaluable check? - and that rule belongs to the caller, not here. Per-check
verdicts also keep information a single run-level outcome would discard.
"""
import json
from pathlib import Path

from guards.verdict import Outcome, Verdict

GUARD = "c3.verdict_traceable_to_probe"

# Which probe result justifies which verdict. Anything else is a mismatch:
# a timeout is not a refusal, and neither is a missing answer an allow.
JUSTIFIES = {"allow": "allowed", "deny": "refused"}


def read_records(path, check_id):
    """Return (entries_for_check_id, error). error is None if the file parsed."""
    entries = []
    for n, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return None, f"probe record line {n} is not valid JSON"
        if event.get("check_id") == check_id:
            entries.append(event)
    return entries, None


def check_verdict_traceable(check_id, verdict, record_path):
    record_path = Path(record_path)
    evidence = {"check_id": check_id, "verdict": verdict,
                "record_file": str(record_path)}

    def cannot(reason):
        return Verdict(GUARD, Outcome.CANNOT_EVALUATE, reason, evidence)

    if verdict not in JUSTIFIES:
        return cannot(f"verdict {verdict!r} is not one this guard knows how to justify")

    if not record_path.is_file():
        return cannot("no probe record at all; the verdict was inferred from the "
                      "probe's absence, not from a probe")
    entries, error = read_records(record_path, check_id)
    if error:
        return cannot(error)
    evidence["records_for_check"] = len(entries)

    phases = [e.get("phase") for e in entries]
    if not entries:
        return cannot("probe record exists but holds no entry for this check; "
                      "nothing ran for this verdict")
    if phases.count("start") != 1 or phases.count("end") != 1:
        # Also catches a stale record from an earlier run appearing alongside a
        # fresh one: two pairs for one check_id is not evidence, it is ambiguity.
        return cannot(f"expected exactly one start and one end for this check, "
                      f"found {phases.count('start')} start / {phases.count('end')} end")

    end = next(e for e in entries if e.get("phase") == "end")
    if "result" not in end:
        return cannot("probe's end record carries no result")
    result = end["result"]
    evidence["probe_result"] = result

    if result == JUSTIFIES[verdict]:
        return Verdict(GUARD, Outcome.PASS,
                       f"verdict {verdict} traceable to a probe that recorded {result}",
                       evidence)
    return Verdict(GUARD, Outcome.FAIL,
                   f"verdict {verdict}, probe recorded {result}; "
                   f"only {JUSTIFIES[verdict]!r} justifies {verdict}", evidence)
