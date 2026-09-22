"""Negative controls for the class 4 guard.

The guard compares two documents: a declaration of expected artefacts and a
manifest. Neither produces the other. These tests break each input in turn
and assert the guard refuses rather than passing.
"""
import pytest

from guards.c4_evidence import check_manifest_covers_expected, read_expected
from guards.verdict import Outcome

D = "a" * 64  # a well-formed sha256 digest; content is irrelevant here


def write_expected(path, names=("one.txt", "two.txt")):
    path.write_text("# a comment\n\n" + "\n".join(names) + "\n")
    return path


def write_manifest(path, names=("one.txt", "two.txt")):
    path.write_text("".join(f"{D}  {n}\n" for n in names))
    return path


@pytest.fixture
def expected(tmp_path):
    return write_expected(tmp_path / "expected.txt")


def outcome(exp, man):
    return check_manifest_covers_expected(exp, man).outcome


# --- decisive outcomes ---

def test_pass_when_manifest_covers_expected(expected, tmp_path):
    man = write_manifest(tmp_path / "m.sha256")
    assert outcome(expected, man) is Outcome.PASS


def test_pass_ignores_order(expected, tmp_path):
    man = write_manifest(tmp_path / "m.sha256", ("two.txt", "one.txt"))
    assert outcome(expected, man) is Outcome.PASS


def test_fail_when_artefact_missing(expected, tmp_path):
    man = write_manifest(tmp_path / "m.sha256", ("one.txt",))
    assert outcome(expected, man) is Outcome.FAIL


def test_fail_when_manifest_empty(expected, tmp_path):
    """The `make clean` case: every hash correct, nothing there."""
    man = tmp_path / "m.sha256"
    man.write_text("")
    assert outcome(expected, man) is Outcome.FAIL


def test_fail_on_swap_where_count_matches(expected, tmp_path):
    """The case a count-based guard passes: same number, wrong file."""
    man = write_manifest(tmp_path / "m.sha256", ("one.txt", "notes.txt"))
    v = check_manifest_covers_expected(expected, man)
    assert v.outcome is Outcome.FAIL
    assert v.evidence["missing"] == ["two.txt"]
    assert v.evidence["unexpected"] == ["notes.txt"]


def test_fail_on_unexpected_extra(expected, tmp_path):
    man = write_manifest(tmp_path / "m.sha256", ("one.txt", "two.txt", "extra.txt"))
    assert outcome(expected, man) is Outcome.FAIL


# --- refusal branches ---

def test_refuses_missing_expectation(tmp_path):
    man = write_manifest(tmp_path / "m.sha256")
    assert outcome(tmp_path / "absent.txt", man) is Outcome.CANNOT_EVALUATE


def test_refuses_empty_expectation(tmp_path):
    """No expectation means nothing to check against: the vacuous pass, closed."""
    exp = tmp_path / "expected.txt"
    exp.write_text("# only comments\n\n")
    man = write_manifest(tmp_path / "m.sha256")
    assert outcome(exp, man) is Outcome.CANNOT_EVALUATE


def test_refuses_duplicate_expectation(tmp_path):
    exp = write_expected(tmp_path / "expected.txt", ("one.txt", "one.txt"))
    man = write_manifest(tmp_path / "m.sha256", ("one.txt",))
    assert outcome(exp, man) is Outcome.CANNOT_EVALUATE


def test_refuses_missing_manifest(expected, tmp_path):
    assert outcome(expected, tmp_path / "absent.sha256") is Outcome.CANNOT_EVALUATE


def test_refuses_malformed_manifest_line(expected, tmp_path):
    man = tmp_path / "m.sha256"
    man.write_text(f"{D}  one.txt\nnot-a-manifest-line\n")
    assert outcome(expected, man) is Outcome.CANNOT_EVALUATE


def test_refuses_short_digest(expected, tmp_path):
    """A truncated digest means the manifest was not written by a real hasher."""
    man = tmp_path / "m.sha256"
    man.write_text("abc123  one.txt\n")
    assert outcome(expected, man) is Outcome.CANNOT_EVALUATE


def test_refuses_duplicate_manifest_entry(expected, tmp_path):
    man = write_manifest(tmp_path / "m.sha256", ("one.txt", "two.txt", "one.txt"))
    assert outcome(expected, man) is Outcome.CANNOT_EVALUATE


# --- parsing ---

def test_expected_ignores_comments_and_blanks(tmp_path):
    exp = tmp_path / "expected.txt"
    exp.write_text("# header\n\n  one.txt  \n\n# mid\ntwo.txt\n")
    assert read_expected(exp) == ["one.txt", "two.txt"]
