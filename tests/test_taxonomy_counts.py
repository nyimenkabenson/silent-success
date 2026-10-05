"""Negative controls for the taxonomy arithmetic check.

Two failure paths, and the tests keep them apart: a count that disagrees with
its own row list is a FAIL, and a line the parser cannot read is a refusal.
Conflating them would make a prose edit look like a defect in the taxonomy.

The mutations are built by regex rather than by quoting a class's text, so
these tests survive the counts changing - which they are about to, when S8
lands.
"""
import re
from pathlib import Path

from guards.verdict import Outcome
from tools.taxonomy_counts import check_taxonomy_counts

DOC = Path("docs/taxonomy.md")


def write_variant(tmp_path, text):
    target = tmp_path / "taxonomy.md"
    target.write_text(text)
    return target


def test_the_real_document_is_consistent():
    verdict = check_taxonomy_counts(DOC)
    assert verdict.outcome is Outcome.PASS, verdict.reason


def test_a_count_that_disagrees_with_its_rows_fails(tmp_path):
    text = re.sub(r"\*\*Instances: (\d+)",
                  lambda m: f"**Instances: {int(m.group(1)) - 1}",
                  DOC.read_text(), count=1)
    verdict = check_taxonomy_counts(write_variant(tmp_path, text))
    assert verdict.outcome is Outcome.FAIL, verdict.reason
    assert "but names" in verdict.reason


def test_an_unreadable_instances_line_refuses(tmp_path):
    text = re.sub(r"\*\*Instances: \d+(?: counted)?\*\*", "**Instances: six**",
                  DOC.read_text(), count=1)
    verdict = check_taxonomy_counts(write_variant(tmp_path, text))
    assert verdict.outcome is Outcome.CANNOT_EVALUATE, verdict.reason
    assert "did not parse" in verdict.reason


def test_a_missing_document_refuses(tmp_path):
    verdict = check_taxonomy_counts(tmp_path / "absent.md")
    assert verdict.outcome is Outcome.CANNOT_EVALUATE, verdict.reason
