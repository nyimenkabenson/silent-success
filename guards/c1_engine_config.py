"""Class 1 guard - the engine's own configuration files.

A second class 1 guard, for a second observable. The existing guard reads
rules_loaded from eve.json, which answers "did my rules take effect". It
cannot answer "did the engine load its own configuration", and a run where
Suricata failed to open three config files still reports rules_loaded: 1 and
one alert - so the first guard passes it.

The check is a hybrid, and the split is stated rather than hidden:

  Positive half - Suricata announces the threshold config on success
  ("Info: threshold-config: Threshold config parsed"). The guard requires
  that line. An absent confirmation is a failure, which a search for error
  text alone could never detect.

  Negative half - reference.config and classification.config are announced
  only when they fail. There is no success line to require, so the guard
  detects the failure markers.

Stated scope: a silent failure of a file Suricata does not announce on
success, in a form that produces no error line, would not be caught. The
positive half covers what can be confirmed; the negative half covers what
can only be denied.
"""
import re
from pathlib import Path

from guards.verdict import Outcome, Verdict

GUARD = "c1.engine_config_read"

# Suricata writes one line per event, with a severity word after the timestamp.
STARTED = "This is Suricata version"
CONFIRMATIONS = {
    "threshold config": "threshold-config: Threshold config parsed",
}
# A config subsystem reporting a problem. The subsystem names end in -config.
PROBLEM = re.compile(r"\b(Error|Warning):\s+([a-z-]+-config):\s+(.+)$")


def check_engine_config_read(log_path):
    log_path = Path(log_path)
    evidence = {"log_file": str(log_path)}

    def cannot(reason):
        return Verdict(GUARD, Outcome.CANNOT_EVALUATE, reason, evidence)

    if not log_path.is_file():
        return cannot("engine log not found")
    lines = [l for l in log_path.read_text().splitlines() if l.strip()]
    evidence["log_lines"] = len(lines)
    if not lines:
        return cannot("engine log is empty")
    if not any(STARTED in l for l in lines):
        # Without the startup banner the guard cannot tell whether Suricata
        # ran at all, so an absent confirmation would mean nothing.
        return cannot("no engine startup banner in the log; cannot tell whether the engine ran")

    problems = []
    for line in lines:
        m = PROBLEM.search(line)
        if m:
            problems.append({"severity": m.group(1), "subsystem": m.group(2),
                             "detail": m.group(3)})
    # Sorted, not file-ordered: Suricata's line order is not stable between
    # runs, so anything recorded from this list would otherwise vary with it.
    problems.sort(key=lambda p: (p["severity"], p["subsystem"], p["detail"]))
    evidence["problems"] = problems

    missing = [name for name, marker in CONFIRMATIONS.items()
               if not any(marker in l for l in lines)]
    evidence["unconfirmed"] = missing

    if not problems and not missing:
        return Verdict(GUARD, Outcome.PASS,
                       f"engine configuration read; {len(CONFIRMATIONS)} confirmation(s) present, "
                       "no configuration problems reported", evidence)

    parts = []
    if problems:
        subsystems = sorted({p["subsystem"] for p in problems})
        # Each failed config produces a failure line and a "please check"
        # advisory, so the line count exceeds the subsystem count.
        parts.append(f"{len(problems)} configuration problem(s) across "
                     f"{len(subsystems)} subsystem(s): {', '.join(subsystems)}")
    if missing:
        parts.append(f"no confirmation that the {', '.join(missing)} was read")
    return Verdict(GUARD, Outcome.FAIL, "; ".join(parts), evidence)
