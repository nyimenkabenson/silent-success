"""The tri-state verdict every guard returns.

PASS, FAIL, or CANNOT_EVALUATE. The third outcome exists because a guard
that cannot find its evidence must never report success:
"I couldn't check" is not "it's fine".
"""
from dataclasses import dataclass, field
from enum import Enum


class Outcome(Enum):
    PASS = "pass"
    FAIL = "fail"
    CANNOT_EVALUATE = "cannot_evaluate"


@dataclass(frozen=True)
class Verdict:
    guard: str
    outcome: Outcome
    reason: str
    evidence: dict = field(default_factory=dict)

    def __bool__(self):
        # Python treats any object as True by default, so `if verdict:` would
        # pass even on FAIL - a silent success inside the guard library itself.
        # Refuse that usage: callers must compare .outcome explicitly.
        raise TypeError("Verdict has no truth value; compare verdict.outcome to Outcome.PASS")

    def to_dict(self):
        return {"guard": self.guard, "outcome": self.outcome.value,
                "reason": self.reason, "evidence": self.evidence}
