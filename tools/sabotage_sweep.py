"""Sabotage every refusal and failure branch in every guard, one at a time, and
record which tests go red.

The rule this enforces is one sabotage per load-bearing test: a branch nothing
turns red is a branch that could be deleted unnoticed. Rather than asserting
that discipline in prose, this walks the guards and produces the map, so a
judge can run it.

A branch with an empty tests_red is a finding, not an error. It is class 5 in
the guards themselves - a check that could only ever pass, because nothing
proves it can fail.

Branches are located by AST, not by text: guards mix a local `cannot()` helper
with direct `Verdict(GUARD, Outcome.FAIL, ...)` returns, and a text search
cannot tell those apart reliably.

  python tools/sabotage_sweep.py              write out/sabotage-map.json
  python tools/sabotage_sweep.py --check      ... and exit 1 on any empty row
  python tools/sabotage_sweep.py --self-test  prove the sweep can find a hole

The original file is restored from memory in a finally block, and the sweep
refuses to start against a dirty working tree so a crashed run is visible.
"""
import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD_DIR = ROOT / "guards"
MAP_PATH = ROOT / "out" / "sabotage-map.json"
# Survives a killed run: the sweep mutates guards in place thirty-odd times,
# so an interrupted run must leave the originals recoverable rather than lost.
BACKUP = ROOT / ".sweep-backup"
NEEDED = ("Verdict", "Outcome", "GUARD")
FAILED = re.compile(r"^FAILED \S+::(\S+)")


def _in_helper(tree, target):
    """True if this return sits inside a nested function named `cannot`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "cannot":
            if node.lineno <= target.lineno <= node.end_lineno:
                return True
    return False


def branches(path):
    """Every return that yields a FAIL or CANNOT_EVALUATE verdict, by AST."""
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        outcome = None
        if isinstance(func, ast.Name) and func.id == "cannot":
            outcome = "CANNOT_EVALUATE"
        elif isinstance(func, ast.Name) and func.id == "Verdict":
            for arg in node.value.args:
                if isinstance(arg, ast.Attribute) and arg.attr in ("FAIL", "CANNOT_EVALUATE"):
                    outcome = arg.attr
        if outcome:
            # A return inside a nested `cannot` helper is not a branch: it is
            # the shared exit every refusal routes through. Sabotaging it blinds
            # them all at once, which is informative as a hub measurement but
            # would double-count against the per-branch rule.
            kind = "helper" if _in_helper(tree, node) else "branch"
            found.append({"line": node.lineno, "end_line": node.end_lineno,
                          "outcome": outcome, "kind": kind})
    return sorted(found, key=lambda b: b["line"])


def patched(text, branch):
    """Replace one return statement with a PASS, keeping its indentation."""
    lines = text.splitlines(keepends=True)
    first = lines[branch["line"] - 1]
    indent = " " * (len(first) - len(first.lstrip()))
    # {} rather than a local name: the sweep must not depend on what the
    # surrounding function happens to call its evidence dict.
    injected = f'{indent}return Verdict(GUARD, Outcome.PASS, "SWEEP", {{}})\n'
    return "".join(lines[:branch["line"] - 1] + [injected] + lines[branch["end_line"]:])


def red_tests():
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q",
                           "--tb=no", "-rf"],
                          cwd=ROOT, capture_output=True, text=True)
    return sorted({m.group(1) for line in proc.stdout.splitlines()
                   if (m := FAILED.match(line))})


def sweep_file(path, verbose=True):
    original = path.read_text()
    found = branches(path)
    if not found:
        # A package marker or a module with no verdict returns. Checking NEEDED
        # before this would refuse on every non-guard file in the directory.
        return []
    missing = [n for n in NEEDED if n not in original]
    if missing:
        raise SystemExit(f"{path.name} does not reference {', '.join(missing)}")

    BACKUP.mkdir(parents=True, exist_ok=True)
    backup = BACKUP / path.name
    backup.write_text(original)
    rows = []
    try:
        for branch in found:
            candidate = patched(original, branch)
            try:
                ast.parse(candidate)
            except SyntaxError as e:
                raise SystemExit(f"{path.name}:{branch['line']} patch does not parse ({e})")
            path.write_text(candidate)
            reds = red_tests()
            rows.append({"line": branch["line"], "kind": branch["kind"],
                         "outcome": branch["outcome"], "tests_red": reds})
            if verbose:
                mark = "  " if reds or branch["kind"] == "helper" else "!!"
                print(f"{mark} {path.name}:{branch['line']:<4} {branch['kind']:7} "
                      f"{branch['outcome']:16} {len(reds)} red")
    finally:
        path.write_text(original)
        backup.unlink(missing_ok=True)
    return rows


def dirty():
    proc = subprocess.run(["git", "status", "--porcelain", "--", "guards"],
                          cwd=ROOT, capture_output=True, text=True)
    return proc.stdout.strip()


def self_test():
    """Plant a branch no test covers and confirm the sweep reports it empty.

    Without this, a sweep that silently found nothing would print the same
    thing as a library with no holes - the failure this project is about,
    in the tool that looks for it.
    """
    probe = GUARD_DIR / "_sweep_self_test.py"
    probe.write_text(
        "from guards.verdict import Outcome, Verdict\n\n"
        "GUARD = 'sweep.self_test'\n\n\n"
        "def never_called():\n"
        "    return Verdict(GUARD, Outcome.FAIL, 'nothing tests this', {})\n")
    try:
        rows = sweep_file(probe, verbose=False)
    finally:
        probe.unlink()
    if len(rows) != 1:
        raise SystemExit(f"self-test: expected 1 branch, found {len(rows)}")
    if rows[0]["tests_red"]:
        raise SystemExit(f"self-test: planted branch reported as covered by "
                         f"{rows[0]['tests_red']}")
    print("self-test passed: the sweep reports an untested branch as untested")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any branch has no test that goes red")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--restore", action="store_true",
                    help="put back guards left modified by an interrupted sweep")
    args = ap.parse_args()

    if args.restore:
        left = sorted(BACKUP.glob("*.py")) if BACKUP.exists() else []
        for b in left:
            (GUARD_DIR / b.name).write_text(b.read_text())
            b.unlink()
            print(f"restored guards/{b.name}")
        if BACKUP.exists():
            BACKUP.rmdir()
        print(f"restored {len(left)} file(s)")
        return 0

    if args.self_test:
        return self_test()

    stale = sorted(BACKUP.glob("*.py")) if BACKUP.exists() else []
    if stale:
        print("REFUSED: a previous sweep did not finish and left backups for "
              f"{', '.join(b.name for b in stale)}")
        print("Run with --restore first.")
        return 1

    if dirty():
        print("REFUSED: guards/ has uncommitted changes; commit or stash them first")
        return 1

    result, holes, n_branch, n_helper = {}, [], 0, 0
    for path in sorted(GUARD_DIR.glob("*.py")):
        rows = sweep_file(path)
        if rows:
            result[f"guards/{path.name}"] = rows
            n_branch += sum(1 for r in rows if r["kind"] == "branch")
            n_helper += sum(1 for r in rows if r["kind"] == "helper")
            # Only branches are held to the rule. A helper is the shared exit
            # every refusal routes through, so its red set is a hub measurement,
            # not evidence about any one branch.
            holes += [f"guards/{path.name}:{r['line']}"
                      for r in rows if r["kind"] == "branch" and not r["tests_red"]]

    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAP_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"\n{n_branch} branch(es) and {n_helper} helper(s) across {len(result)} "
          f"guards -> {MAP_PATH.relative_to(ROOT)}")

    if holes:
        print(f"{len(holes)} branch(es) with no test that goes red:")
        for h in holes:
            print(f"  {h}")
        return 1 if args.check else 0
    print("every branch load-bearing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
