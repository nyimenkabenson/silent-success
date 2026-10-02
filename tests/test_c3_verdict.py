"""Negative controls for the class 3 guard.

The guard has one signal - the probe's own record - expressed through two
branches: the record must exist as a complete pair, and the recorded result
must justify the verdict. The tests exercise each branch separately so a
sabotage of either turns a distinct set red.
"""
import json

import pytest

from guards.c3_verdict import check_verdict_traceable
from guards.verdict import Outcome

CID = "CHK-01"


def write_records(path, *events):
    path.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
    return path


def pair(check_id=CID, result="refused"):
    return ({"check_id": check_id, "phase": "start"},
            {"check_id": check_id, "phase": "end", "result": result})


@pytest.fixture
def rec(tmp_path):
    return tmp_path / "probe.jsonl"


def outcome(verdict, path, check_id=CID):
    return check_verdict_traceable(check_id, verdict, path).outcome


# --- the two decisive outcomes ---

def test_allow_justified_by_allowed(rec):
    write_records(rec, *pair(result="allowed"))
    assert outcome("allow", rec) is Outcome.PASS


def test_deny_justified_by_refused(rec):
    write_records(rec, *pair(result="refused"))
    assert outcome("deny", rec) is Outcome.PASS


# --- the comparison branch: a result that does not justify the verdict ---

def test_deny_on_timeout_fails(rec):
    """The class 3 case in miniature: the probe ran, reached the target, and
    could not determine anything. A timeout is not a refusal."""
    write_records(rec, *pair(result="timeout"))
    v = check_verdict_traceable(CID, "deny", rec)
    assert v.outcome is Outcome.FAIL
    assert "timeout" in v.reason
    assert v.evidence["probe_result"] == "timeout"


def test_allow_on_refused_fails(rec):
    write_records(rec, *pair(result="refused"))
    assert outcome("allow", rec) is Outcome.FAIL


def test_deny_on_allowed_fails(rec):
    write_records(rec, *pair(result="allowed"))
    assert outcome("deny", rec) is Outcome.FAIL


# --- the existence branch: no complete pair to judge against ---

def test_refuses_when_no_record_file(tmp_path):
    """The verdict was inferred from the probe's absence, not from a probe."""
    v = check_verdict_traceable(CID, "deny", tmp_path / "absent.jsonl")
    assert v.outcome is Outcome.CANNOT_EVALUATE
    assert "absence" in v.reason


def test_refuses_when_record_file_is_empty(rec):
    rec.write_text("")
    assert outcome("deny", rec) is Outcome.CANNOT_EVALUATE


def test_refuses_when_no_entry_for_this_check(rec):
    write_records(rec, *pair(check_id="CHK-OTHER"))
    assert outcome("deny", rec) is Outcome.CANNOT_EVALUATE


def test_refuses_on_start_without_end(rec):
    """The probe began and died: no result to judge against."""
    write_records(rec, {"check_id": CID, "phase": "start"})
    assert outcome("deny", rec) is Outcome.CANNOT_EVALUATE


def test_refuses_on_end_without_start(rec):
    write_records(rec, {"check_id": CID, "phase": "end", "result": "refused"})
    assert outcome("deny", rec) is Outcome.CANNOT_EVALUATE


def test_refuses_on_two_pairs_for_one_check(rec):
    """A stale record from an earlier run beside a fresh one. Two pairs for one
    check_id is ambiguity, not evidence - carryover surfacing inside class 3."""
    write_records(rec, *pair(result="refused"), *pair(result="allowed"))
    assert outcome("deny", rec) is Outcome.CANNOT_EVALUATE


def test_refuses_when_end_has_no_result(rec):
    write_records(rec, {"check_id": CID, "phase": "start"},
                  {"check_id": CID, "phase": "end"})
    assert outcome("deny", rec) is Outcome.CANNOT_EVALUATE


def test_refuses_on_malformed_record_line(rec):
    rec.write_text(json.dumps({"check_id": CID, "phase": "start"}) + "\ntruncated{\n")
    assert outcome("deny", rec) is Outcome.CANNOT_EVALUATE


def test_refuses_unknown_verdict(rec):
    """A verdict the guard has no justification rule for is not judged."""
    write_records(rec, *pair(result="refused"))
    assert outcome("maybe", rec) is Outcome.CANNOT_EVALUATE
