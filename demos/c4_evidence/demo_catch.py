"""Class 4 - demo_catch: the guard separates a real build from an empty one.

Runs four builds - complete, cleaned, partial, and a swap where the file
count still matches - and judges each two ways: the naive check (verify
passed) and the class 4 guard (does the manifest cover what was declared).
Writes out/c4/results.json. Exits 0 if the guard separated them as claimed.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from guards.c4_evidence import check_manifest_covers_expected
from guards.verdict import Outcome

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "out" / "c4" / "build"
MANIFEST = Path("out/c4/manifest.sha256")
EXPECTED = Path("demos/c4_evidence/expected.txt")

# The claim, stated before anything runs. The naive check passes every case.
CLAIM = {
    "complete": Outcome.PASS,
    "cleaned": Outcome.FAIL,
    "partial": Outcome.FAIL,
    "swapped": Outcome.FAIL,
}


def build(*steps):
    proc = subprocess.run([sys.executable, "demos/c4_evidence/build.py", *steps],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout


def case(name):
    """Set each case up, ending with manifest+verify. Returns the verify exit code."""
    shutil.rmtree(ROOT / "out" / "c4", ignore_errors=True)
    build("build")
    if name == "cleaned":
        build("clean")
    elif name == "partial":
        (BUILD / "report.md").unlink()
        (BUILD / "results.xml").unlink()
    elif name == "swapped":
        (BUILD / "report.md").rename(BUILD / "notes.md")
    code, _ = build("manifest", "verify")
    return code


def main():
    os.chdir(ROOT)
    rows = {}
    for name in CLAIM:
        code = case(name)
        rows[name] = {
            "verify_exit": code,
            "manifest_entries": len([l for l in MANIFEST.read_text().splitlines() if l.strip()]),
            "naive": "green" if code == 0 else "red",
            "guard": check_manifest_covers_expected(EXPECTED, MANIFEST),
        }

    print(f"\n{'case':10} {'entries':>7}  {'naive':6} guard")
    for name, r in rows.items():
        v = r["guard"]
        print(f"{name:10} {r['manifest_entries']:>7}  {r['naive']:6} {v.outcome.value}: {v.reason}")

    results = {
        name: {"verify_exit": r["verify_exit"], "manifest_entries": r["manifest_entries"],
               "naive": r["naive"], "guard": r["guard"].to_dict()}
        for name, r in rows.items()
    }
    out = ROOT / "out" / "c4" / "results.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {out.relative_to(ROOT)}")

    held = (all(r["naive"] == "green" for r in rows.values())
            and all(rows[n]["guard"].outcome is o for n, o in CLAIM.items()))
    if held:
        print("DEMONSTRATED: verify passed all four; the guard failed the three that were wrong.")
        print("Note `swapped`: the entry count matches, so a count-based check would pass it.")
        return 0
    print("NOT DEMONSTRATED: results differ from the claim above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
