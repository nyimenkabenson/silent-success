"""Negative controls for the class 6 guard.

Class 6 judges two inputs together: a recorded pre-state and an output count.
The grid matters more than either input alone, so these tests walk every cell
of it, then break each input in turn and assert the guard refuses.
"""
import json

import pytest

from guards.c6_carryover import check_output_free_of_prior_runs
from guards.verdict import Outcome


def write_declared(path, body="# a comment\n1\n"):
    path.write_text(body)
    return path


def write_pre_state(path, existed=False, extra=None):
    doc = {"existed": existed}
    if existed:
        doc.update({"alerts": 1})
    if extra:
        doc.update(extra)
    path.write_text(json.dumps(doc))
    return path


def write_eve(path, alerts=1):
    lines = [json.dumps({"event_type": "alert", "n": i}) for i in range(alerts)]
    lines.append(json.dumps({"event_type": "stats"}))
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.fixture
def declared(tmp_path):
    return write_declared(tmp_path / "expected_alerts.txt")


def outcome(dec, pre, eve):
    return check_output_free_of_prior_runs(dec, pre, eve).outcome


# --- the grid ---

def test_clean_slate_and_expected_count_passes(declared, tmp_path):
    pre = write_pre_state(tmp_path / "pre.json", existed=False)
    eve = write_eve(tmp_path / "eve.json", alerts=1)
    assert outcome(declared, pre, eve) is Outcome.PASS


def test_clean_slate_with_excess_fails_but_not_as_carryover(declared, tmp_path):
    """The slate was clean, so excess events came from somewhere else. The
    guard must say so rather than blaming its own class."""
    pre = write_pre_state(tmp_path / "pre.json", existed=False)
    eve = write_eve(tmp_path / "eve.json", alerts=2)
    v = check_output_free_of_prior_runs(declared, pre, eve)
    assert v.outcome is Outcome.FAIL
    assert "not carryover" in v.reason


def test_clean_slate_with_too_few_fails(declared, tmp_path):
    pre = write_pre_state(tmp_path / "pre.json", existed=False)
    eve = write_eve(tmp_path / "eve.json", alerts=0)
    assert outcome(declared, pre, eve) is Outcome.FAIL


def test_dirty_slate_with_excess_fails_as_carryover(declared, tmp_path):
    pre = write_pre_state(tmp_path / "pre.json", existed=True)
    eve = write_eve(tmp_path / "eve.json", alerts=2)
    v = check_output_free_of_prior_runs(declared, pre, eve)
    assert v.outcome is Outcome.FAIL
    assert "carryover" in v.reason


def test_dirty_slate_with_matching_count_still_fails(declared, tmp_path):
    """The row that matters: a violated precondition is a failure even when
    the count looks right, because an appending run and a truncating run are
    indistinguishable from the count alone."""
    pre = write_pre_state(tmp_path / "pre.json", existed=True)
    eve = write_eve(tmp_path / "eve.json", alerts=1)
    v = check_output_free_of_prior_runs(declared, pre, eve)
    assert v.outcome is Outcome.FAIL
    assert "slate was not clean" in v.reason


def test_dirty_slate_failure_shows_before_and_after(declared, tmp_path):
    pre = write_pre_state(tmp_path / "pre.json", existed=True)
    eve = write_eve(tmp_path / "eve.json", alerts=2)
    v = check_output_free_of_prior_runs(declared, pre, eve)
    assert v.evidence["pre_state_alerts"] == 1
    assert "held 1 alert(s) before this run, 2 now" in v.reason


# --- refusal branches ---

def test_refuses_missing_declaration(tmp_path):
    pre = write_pre_state(tmp_path / "pre.json")
    eve = write_eve(tmp_path / "eve.json")
    assert outcome(tmp_path / "absent.txt", pre, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_declaration_with_two_values(tmp_path):
    dec = write_declared(tmp_path / "d.txt", "1\n2\n")
    pre = write_pre_state(tmp_path / "pre.json")
    eve = write_eve(tmp_path / "eve.json")
    assert outcome(dec, pre, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_declaration_with_no_value(tmp_path):
    dec = write_declared(tmp_path / "d.txt", "# only a comment\n")
    pre = write_pre_state(tmp_path / "pre.json")
    eve = write_eve(tmp_path / "eve.json")
    assert outcome(dec, pre, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_non_numeric_declaration(tmp_path):
    dec = write_declared(tmp_path / "d.txt", "one\n")
    pre = write_pre_state(tmp_path / "pre.json")
    eve = write_eve(tmp_path / "eve.json")
    assert outcome(dec, pre, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_zero_declaration(tmp_path):
    """Zero expected and zero found would pass vacuously - the same hazard as
    the empty rules file in class 1 and the empty expectation in class 4."""
    dec = write_declared(tmp_path / "d.txt", "0\n")
    pre = write_pre_state(tmp_path / "pre.json")
    eve = write_eve(tmp_path / "eve.json", alerts=0)
    assert outcome(dec, pre, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_missing_pre_state(declared, tmp_path):
    """Without a pre-state, carryover can be neither shown nor ruled out."""
    eve = write_eve(tmp_path / "eve.json", alerts=2)
    assert outcome(declared, tmp_path / "absent.json", eve) is Outcome.CANNOT_EVALUATE


def test_refuses_malformed_pre_state(declared, tmp_path):
    pre = tmp_path / "pre.json"
    pre.write_text("{not json")
    eve = write_eve(tmp_path / "eve.json")
    assert outcome(declared, pre, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_pre_state_without_existed(declared, tmp_path):
    pre = tmp_path / "pre.json"
    pre.write_text(json.dumps({"size": 10}))
    eve = write_eve(tmp_path / "eve.json")
    assert outcome(declared, pre, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_non_boolean_existed(declared, tmp_path):
    """"yes" is truthy in Python: a string here would silently take the dirty
    branch without ever having been a boolean."""
    pre = tmp_path / "pre.json"
    pre.write_text(json.dumps({"existed": "yes"}))
    eve = write_eve(tmp_path / "eve.json")
    assert outcome(declared, pre, eve) is Outcome.CANNOT_EVALUATE


def test_refuses_missing_output(declared, tmp_path):
    pre = write_pre_state(tmp_path / "pre.json")
    assert outcome(declared, pre, tmp_path / "absent.json") is Outcome.CANNOT_EVALUATE


def test_refuses_malformed_output_line(declared, tmp_path):
    pre = write_pre_state(tmp_path / "pre.json")
    eve = tmp_path / "eve.json"
    eve.write_text(json.dumps({"event_type": "alert"}) + "\ntruncated{\n")
    assert outcome(declared, pre, eve) is Outcome.CANNOT_EVALUATE


def test_counts_alerts_not_all_events(declared, tmp_path):
    """The guard counts alerts specifically. Every other fixture here writes
    only alert and stats events, so an "any event" guard would have been caught
    by accident rather than by claim - this pins it down with unrelated event
    types present."""
    pre = write_pre_state(tmp_path / "pre.json", existed=False)
    eve = tmp_path / "eve.json"
    eve.write_text("\n".join(json.dumps(e) for e in [
        {"event_type": "flow"},
        {"event_type": "alert"},
        {"event_type": "dns"},
        {"event_type": "http"},
        {"event_type": "stats"},
    ]) + "\n")
    v = check_output_free_of_prior_runs(declared, pre, eve)
    assert v.evidence["alerts"] == 1
    assert v.outcome is Outcome.PASS


def test_file_with_no_alerts_counts_zero(declared, tmp_path):
    """A narrow tripwire on the counting logic alone: only flow events, so
    the count must be zero regardless of the surrounding grid. Isolates the
    count from the pre-state and declaration paths, which the other tests
    exercise together."""
    pre = write_pre_state(tmp_path / "pre.json", existed=False)
    eve = tmp_path / "eve.json"
    eve.write_text("\n".join(json.dumps({"event_type": "flow"}) for _ in range(4)) + "\n")
    v = check_output_free_of_prior_runs(declared, pre, eve)
    assert v.evidence["alerts"] == 0


def test_refuses_unreadable_pre_state_count(declared, tmp_path):
    """The wrapper admitting it could not read the prior state. Failing here
    would claim the slate was dirty; what the guard knows is that it cannot
    tell, so it refuses."""
    pre = tmp_path / "pre.json"
    pre.write_text(json.dumps({"existed": True, "alerts": None,
                               "note": "output contains a line that is not valid JSON"}))
    eve = write_eve(tmp_path / "eve.json", alerts=2)
    v = check_output_free_of_prior_runs(declared, pre, eve)
    assert v.outcome is Outcome.CANNOT_EVALUATE
    assert "could not be read" in v.reason


def test_absent_pre_state_needs_no_count(declared, tmp_path):
    """A clean slate has no alert count to record, and that must stay a pass -
    the refusal above applies only when a prior state existed."""
    pre = tmp_path / "pre.json"
    pre.write_text(json.dumps({"existed": False}))
    eve = write_eve(tmp_path / "eve.json", alerts=1)
    assert outcome(declared, pre, eve) is Outcome.PASS
