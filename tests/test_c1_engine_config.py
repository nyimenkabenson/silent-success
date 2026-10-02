"""Negative controls for the engine-config guard.

The guard is a hybrid: a positive half requiring a confirmation line, and a
negative half detecting failure markers. The tests exercise each half alone,
so a sabotage of either turns a distinct set red.
"""
from pathlib import Path

import pytest

from guards.c1_engine_config import check_engine_config_read
from guards.verdict import Outcome

FIXTURES = Path("demos/c1_config/fixtures")
CLEAN = FIXTURES / "engine-clean.log"
DEGRADED = FIXTURES / "engine-degraded.log"


def outcome(path):
    return check_engine_config_read(path).outcome


# --- against the captured logs ---

def test_clean_log_passes():
    assert outcome(CLEAN) is Outcome.PASS


def test_degraded_log_fails_on_both_halves():
    """The real degradation: three config files unreadable, and the threshold
    confirmation absent because that file was one of them."""
    v = check_engine_config_read(DEGRADED)
    assert v.outcome is Outcome.FAIL
    assert v.evidence["problems"], "negative half should have found failure markers"
    assert v.evidence["unconfirmed"] == ["threshold config"]
    assert "subsystem(s)" in v.reason
    assert "no confirmation" in v.reason


# --- each half alone ---

def test_positive_half_alone(tmp_path):
    """Confirmation absent, no error markers: only the positive half can see
    this, and a guard built from error patterns alone would pass it."""
    lines = [l for l in CLEAN.read_text().splitlines()
             if "Threshold config parsed" not in l]
    log = tmp_path / "s.log"
    log.write_text("\n".join(lines) + "\n")
    v = check_engine_config_read(log)
    assert v.outcome is Outcome.FAIL
    assert not v.evidence["problems"]
    assert v.evidence["unconfirmed"] == ["threshold config"]


def test_negative_half_alone(tmp_path):
    """Confirmation present, but another subsystem reported a problem."""
    log = tmp_path / "s.log"
    log.write_text(CLEAN.read_text() +
                   '[1 - Suricata-Main] 2026-10-02 14:50:56 Error: reference-config: '
                   'Error opening file: "/etc/suricata/reference.config": Permission denied\n')
    v = check_engine_config_read(log)
    assert v.outcome is Outcome.FAIL
    assert len(v.evidence["problems"]) == 1
    assert not v.evidence["unconfirmed"]


# --- refusal branches ---

def test_refuses_missing_log(tmp_path):
    assert outcome(tmp_path / "absent.log") is Outcome.CANNOT_EVALUATE


def test_refuses_empty_log(tmp_path):
    log = tmp_path / "s.log"
    log.write_text("\n\n   \n")
    assert outcome(log) is Outcome.CANNOT_EVALUATE


def test_refuses_log_without_startup_banner(tmp_path):
    """Without the banner the guard cannot tell whether the engine ran, so an
    absent confirmation would mean nothing."""
    log = tmp_path / "s.log"
    log.write_text("[1 - Suricata-Main] 2026-10-02 14:50:56 Info: cpu: CPUs/cores online: 4\n")
    assert outcome(log) is Outcome.CANNOT_EVALUATE


def test_refuses_before_judging_an_absent_confirmation(tmp_path):
    """A log with no banner and no confirmation must refuse, not fail: the
    refusal has to be checked before the positive half runs."""
    log = tmp_path / "s.log"
    log.write_text("some unrelated output\n")
    v = check_engine_config_read(log)
    assert v.outcome is Outcome.CANNOT_EVALUATE
    assert "startup banner" in v.reason
