"""Temporarily break a guard, to prove its tests can go red.

Refuses if the target text is not found exactly once. A sabotage that
silently does nothing produces a green run that proves nothing - the
failure this project is about, in the tool that verifies it.

Usage:  python tools/sabotage.py guards/c4_evidence.py "<exact line>"
Restore with: git checkout <file>
"""
import sys
from pathlib import Path

REPLACEMENT = '        return Verdict(GUARD, Outcome.PASS, "SABOTAGE", evidence)'


def main(path, target):
    p = Path(path)
    text = p.read_text()
    n = text.count(target)
    if n != 1:
        print(f"REFUSED: target found {n} times in {path}; expected exactly 1")
        return 1
    p.write_text(text.replace(target, REPLACEMENT))
    print(f"sabotaged {path}: one branch now returns PASS. Restore with: git checkout {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
