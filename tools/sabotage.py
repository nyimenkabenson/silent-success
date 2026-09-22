"""Temporarily break a guard, to prove its tests can go red.

Refuses unless the target text appears exactly once, the names the injected
line needs are present, and the patched file still parses. Without those
checks a bad injection breaks the module, pytest errors, and the run goes
red for the wrong reason - a false red that looks exactly like a working
sabotage. The original file is restored on any refusal.

Usage:  python tools/sabotage.py guards/c4_evidence.py "<exact line>"
Restore with: git checkout <file>
"""
import ast
import subprocess
import sys
from pathlib import Path

NEEDED = ("Verdict", "Outcome", "GUARD")


def refuse_unless_restorable(path):
    """Return a refusal reason, or None if `git checkout` can restore this file.

    Restoration is `git checkout <path>`, which silently discards uncommitted
    edits and does nothing at all for an untracked file. So the tool refuses
    to touch anything it could not put back: a restore path that can quietly
    drop work does not belong in a tool built to refuse silent failure.
    """
    try:
        proc = subprocess.run(["git", "status", "--porcelain", "--", str(path)],
                              capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "not inside a git repository, so there is no way to restore the file"
    status = proc.stdout.strip()
    if not status:
        return None
    if status.startswith("??"):
        return "file is untracked, so `git checkout` would not restore it"
    return f"file has uncommitted changes ({status.split()[0]}); commit or stash them first"


def main(path, target):
    p = Path(path)
    original = p.read_text()

    reason = refuse_unless_restorable(p)
    if reason:
        print(f"REFUSED: {reason}")
        return 1

    if "SABOTAGE" in original:
        print(f"REFUSED: {path} is already sabotaged; restore it first")
        return 1

    n = original.count(target)
    if n != 1:
        print(f"REFUSED: target found {n} times in {path}; expected exactly 1")
        return 1

    missing = [name for name in NEEDED if name not in original]
    if missing:
        print(f"REFUSED: {path} does not reference {', '.join(missing)}; "
              "the injected line would raise NameError, not subvert the branch")
        return 1

    indent = " " * (len(target) - len(target.lstrip()))
    patched = original.replace(
        target, f'{indent}return Verdict(GUARD, Outcome.PASS, "SABOTAGE", evidence)')

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"REFUSED: patched file does not parse ({e}); nothing written")
        return 1

    p.write_text(patched)
    try:
        ast.parse(p.read_text())
    except SyntaxError:
        p.write_text(original)
        print("REFUSED: patched file did not parse after writing; original restored")
        return 1

    print(f"sabotaged {path}: one branch now returns PASS. Restore with: git checkout {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
