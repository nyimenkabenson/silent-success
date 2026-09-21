"""Class 1 guard - configuration not in effect.

Principle: read back what the running tool actually loaded; never trust
what you passed it. Suricata reports its effective rule count in eve.json
stats events, under stats.detect.engines.
"""
import json
from pathlib import Path

from guards.verdict import Outcome, Verdict

GUARD = "c1.suricata_rules_in_effect"


def count_rules(rules_path):
    """One rule per non-blank, non-comment line.

    Known limitation: a rule split across lines with trailing backslashes is
    over-counted. That makes the guard FAIL, never falsely PASS.
    """
    lines = Path(rules_path).read_text().splitlines()
    return sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))


def check_rules_in_effect(rules_path, eve_path):
    rules_path, eve_path = Path(rules_path), Path(eve_path)
    evidence = {"rules_file": str(rules_path), "eve_file": str(eve_path)}

    def cannot(reason):
        return Verdict(GUARD, Outcome.CANNOT_EVALUATE, reason, evidence)

    if not rules_path.is_file():
        return cannot("rules file not found")
    expected = count_rules(rules_path)
    evidence["expected"] = expected
    if expected == 0:
        return cannot("rules file contains no rules, so there is nothing to verify")

    if not eve_path.is_file():
        return cannot("eve.json not found")
    stats_events = []
    for n, line in enumerate(eve_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return cannot(f"eve.json line {n} is not valid JSON")
        if event.get("event_type") == "stats":
            stats_events.append(event)
    evidence["stats_events_seen"] = len(stats_events)
    if not stats_events:
        return cannot("no stats event in eve.json, so the loaded-rule count is unknown")

    engines = stats_events[-1].get("stats", {}).get("detect", {}).get("engines")
    if not isinstance(engines, list) or len(engines) != 1:
        return cannot("expected exactly one detect engine in stats; refusing to guess")
    try:
        loaded = engines[0]["rules_loaded"]
        failed = engines[0]["rules_failed"]
        skipped = engines[0]["rules_skipped"]
    except KeyError as missing:
        return cannot(f"stats engine entry has no {missing} field")
    evidence.update(loaded=loaded, failed=failed, skipped=skipped)

    if loaded == expected and failed == 0 and skipped == 0:
        return Verdict(GUARD, Outcome.PASS, f"all {expected} rule(s) in effect", evidence)
    return Verdict(GUARD, Outcome.FAIL,
                   f"{loaded} of {expected} rule(s) in effect ({failed} failed, {skipped} skipped)",
                   evidence)
