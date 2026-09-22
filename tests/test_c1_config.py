"""Negative controls for the class 1 guard.

Each test breaks the guard's evidence deliberately and asserts it refuses.
A guard whose refusal paths have never run is an untested guard: these make
every CANNOT_EVALUATE branch fire at least once, on purpose.
"""
import json

import pytest

from guards.c1_config import check_rules_in_effect, count_rules
from guards.verdict import Outcome

RULE = ('alert icmp any any -> any any (msg:"t"; itype:8; sid:1000001; rev:1;)\n')


def write_eve(path, *, loaded=1, failed=0, skipped=0, engines=None, stats=True):
    """Write a minimal eve.json shaped like real Suricata output."""
    lines = [json.dumps({"event_type": "alert"})]
    if stats:
        if engines is None:
            engines = [{"rules_loaded": loaded, "rules_failed": failed,
                        "rules_skipped": skipped}]
        lines.append(json.dumps(
            {"event_type": "stats", "stats": {"detect": {"engines": engines}}}))
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.fixture
def rules(tmp_path):
    p = tmp_path / "demo.rules"
    p.write_text(RULE)
    return p


def outcome(rules_path, eve_path):
    return check_rules_in_effect(rules_path, eve_path).outcome


# --- the two decisive outcomes, on well-formed evidence ---

def test_pass_when_rule_count_matches(rules, tmp_path):
    eve = write_eve(tmp_path / "eve.json", loaded=1)
    assert outcome(rules, eve) is Outcome.PASS


def test_fail_when_nothing_loaded(rules, tmp_path):
    eve = write_eve(tmp_path / "eve.json", loaded=0, failed=1)
    assert outcome(rules, eve) is Outcome.FAIL


def test_fail_when_rule_silently_skipped(rules, tmp_path):
    """Suricata can skip a rule without failing it: still not in effect."""
    eve = write_eve(tmp_path / "eve.json", loaded=0, skipped=1)
    assert outcome(rules, eve) is Outcome.FAIL


# --- the refusal branches: none of these may ever become PASS ---

def test_refuses_missing_rules_file(tmp_path):
    eve = write_eve(tmp_path / "eve.json")
    assert outcome(tmp_path / "absent.rules", eve) is Outcome.CANNOT_EVALUATE


def test_refuses_empty_rules_file(tmp_path):
    """0 expected and 0 loaded would otherwise pass vacuously."""
    empty = tmp_path / "empty.rules"
    empty.write_text("# only a comment\n\n")
    eve = write_eve(tmp_path / "eve.json", loaded=0)
    assert outcome(empty, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_missing_eve(rules, tmp_path):
    assert outcome(rules, tmp_path / "absent.json") is Outcome.CANNOT_EVALUATE


def test_refuses_malformed_json(rules, tmp_path):
    eve = tmp_path / "eve.json"
    eve.write_text('{"event_type":"stats"\n')  # truncated, as a killed run leaves it
    assert outcome(rules, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_eve_without_stats(rules, tmp_path):
    eve = write_eve(tmp_path / "eve.json", stats=False)
    assert outcome(rules, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_multiple_engines(rules, tmp_path):
    """Multi-tenant Suricata: we have never seen it, so we refuse to guess."""
    eve = write_eve(tmp_path / "eve.json", engines=[
        {"rules_loaded": 1, "rules_failed": 0, "rules_skipped": 0},
        {"rules_loaded": 0, "rules_failed": 1, "rules_skipped": 0},
    ])
    assert outcome(rules, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_engine_missing_field(rules, tmp_path):
    """A future schema change drops a field: refuse, never assume zero."""
    eve = write_eve(tmp_path / "eve.json", engines=[{"rules_loaded": 1}])
    assert outcome(rules, eve) is Outcome.CANNOT_EVALUATE


# --- rule counting ---

def test_count_ignores_comments_and_blanks(tmp_path):
    p = tmp_path / "mixed.rules"
    p.write_text(f"# a comment\n\n{RULE}   \n{RULE}")
    assert count_rules(p) == 2


# --- the verdict object itself ---

def test_verdict_refuses_truthiness(rules, tmp_path):
    """`if verdict:` would be green on every FAIL - the library refuses to be
    used that way (D-008)."""
    eve = write_eve(tmp_path / "eve.json", loaded=0, failed=1)
    v = check_rules_in_effect(rules, eve)
    with pytest.raises(TypeError):
        bool(v)


def test_verdict_serializes(rules, tmp_path):
    """results.json is written from to_dict(), so it must be JSON-safe."""
    eve = write_eve(tmp_path / "eve.json", loaded=1)
    d = check_rules_in_effect(rules, eve).to_dict()
    assert json.loads(json.dumps(d))["outcome"] == "pass"
