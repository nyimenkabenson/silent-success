"""Negative controls for the engine-config guard.

The guard is a hybrid: a positive half requiring a confirmation line, and a
negative half detecting failure markers. The tests exercise each half alone,
so a sabotage of either turns a distinct set red.
"""
import random
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


# --- order independence ---
#
# Suricata is multi-threaded and the order of its console lines is not stable
# between runs: on 2026-10-04 the same unchanged command emitted the "no rules
# were loaded" warning and the rule-vars error in opposite order twenty minutes
# apart. Outcome and reason are built from presence (any), counts (len) and
# sorted names, so neither may depend on where a line sits.

PERMUTATIONS = 12


def shuffled_copy(src, dest, seed):
    """Same lines, different order.

    The seed is fixed deliberately: a randomly ordered shuffle would make this
    test non-deterministic, which is the defect it exists to rule out.
    """
    lines = src.read_text().splitlines()
    random.Random(seed).shuffle(lines)
    dest.write_text("\n".join(lines) + "\n")
    return dest


@pytest.mark.parametrize("fixture", [CLEAN, DEGRADED], ids=["clean", "degraded"])
def test_verdict_survives_reordered_log(fixture, tmp_path):
    baseline = check_engine_config_read(fixture)
    for seed in range(PERMUTATIONS):
        target = shuffled_copy(fixture, tmp_path / f"shuffled-{seed}.log", seed)
        got = check_engine_config_read(target)
        assert got.outcome is baseline.outcome, f"seed {seed} changed the outcome"
        assert got.reason == baseline.reason, f"seed {seed} changed the reason"


@pytest.mark.parametrize("fixture", [CLEAN, DEGRADED], ids=["clean", "degraded"])
def test_verdict_survives_a_reversed_log(fixture, tmp_path):
    """The extreme permutation, asserted rather than left to chance."""
    baseline = check_engine_config_read(fixture)
    target = tmp_path / "reversed.log"
    target.write_text("\n".join(reversed(fixture.read_text().splitlines())) + "\n")
    got = check_engine_config_read(target)
    assert got.outcome is baseline.outcome
    assert got.reason == baseline.reason


def test_reordered_log_reports_an_identical_problem_list(tmp_path):
    """The guard sorts its problem list, so a reordered log yields a list that
    is identical, not merely the same members. Anything recorded downstream,
    results.json included, is then stable under Suricata's line order.
    """
    baseline = check_engine_config_read(DEGRADED)
    got = check_engine_config_read(
        shuffled_copy(DEGRADED, tmp_path / "shuffled.log", 7))
    assert len(baseline.evidence["problems"]) > 1, \
        "fixture must hold several problems for this comparison to mean anything"
    assert got.evidence["problems"] == baseline.evidence["problems"]
