"""Class 4 - demo_fail: a manifest that verifies perfectly and describes nothing.

Runs an ordinary build, cleans the output, then hashes and verifies. Every
statement the pipeline makes is true. Exits 0 if the failure reproduced.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "out" / "c4" / "build"
MANIFEST = ROOT / "out" / "c4" / "manifest.sha256"


def run(*steps):
    proc = subprocess.run([sys.executable, str(Path("demos/c4_evidence/build.py")), *steps],
                          capture_output=True, text=True)
    print(proc.stdout, end="")
    return proc.returncode


def main():
    import os, shutil
    os.chdir(ROOT)
    shutil.rmtree(ROOT / "out" / "c4", ignore_errors=True)  # class 6: clean slate

    code = run("build", "clean", "manifest", "verify")
    lines = [l for l in MANIFEST.read_text().splitlines() if l.strip()]
    files = [p for p in BUILD.rglob("*") if p.is_file()]

    print("\nWhat the pipeline sees")
    print(f"  verify exit code   : {code}")
    print(f"  manifest entries   : {len(lines)}")
    hashes = "yes (there are none to be wrong)" if not lines else f"yes, for all {len(lines)}"
    print(f"  every hash correct : {hashes}")
    print(f"  pipeline verdict   : {'VERIFIED' if code == 0 else 'FAILED'}")
    print(f"\nWhat is actually there")
    print(f"  files in {BUILD.relative_to(ROOT)} : {len(files)}")

    if code == 0 and not lines and not files:
        print("\nREPRODUCED: verify passed over an empty manifest describing an empty tree.")
        print("Run demo_catch.py to see the artefacts that should have been there.")
        return 0
    print("\nNOT REPRODUCED: the build did not behave as claimed here.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
