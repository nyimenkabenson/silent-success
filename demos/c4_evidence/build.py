"""A small build: produce artefacts, hash them into a manifest, verify it.

Deliberately ordinary. Nothing here knows about silent success - the point
is that a correct, unremarkable build pipeline produces evidence that can
describe a state that no longer exists.
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "out" / "c4" / "build"
MANIFEST = ROOT / "out" / "c4" / "manifest.sha256"

# What a complete build produces. Fixed content, so hashes are stable.
ARTEFACTS = {
    "topology.yml": "name: demo\nnodes: 3\n",
    "rules.conf": "alert icmp any any -> any any (sid:1;)\n",
    "results.xml": "<testsuite tests='3' failures='0'/>\n",
    "report.md": "# Build report\nAll checks passed.\n",
    "checksums.txt": "placeholder\n",
}


def build():
    BUILD.mkdir(parents=True, exist_ok=True)
    for name, content in ARTEFACTS.items():
        (BUILD / name).write_text(content)
    print(f"build: wrote {len(ARTEFACTS)} artefacts to {BUILD}")


def clean():
    """Remove build output, as `make clean` does."""
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True, exist_ok=True)
    print(f"clean: emptied {BUILD}")


def manifest():
    """Hash every file in the build directory into a manifest."""
    lines = []
    for path in sorted(BUILD.rglob("*")):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(BUILD)}")
    MANIFEST.write_text("\n".join(lines) + "\n" if lines else "")
    print(f"manifest: hashed {len(lines)} file(s) into {MANIFEST}")


def verify():
    """Check every file named in the manifest still matches its hash."""
    entries = [l.split("  ", 1) for l in MANIFEST.read_text().splitlines() if l.strip()]
    for digest, name in entries:
        path = BUILD / name
        if not path.is_file():
            print(f"verify: FAIL - {name} is missing")
            return 1
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            print(f"verify: FAIL - {name} does not match its hash")
            return 1
    print(f"verify: OK - {len(entries)} file(s) match the manifest")
    return 0


if __name__ == "__main__":
    steps = {"build": build, "clean": clean, "manifest": manifest, "verify": verify}
    code = 0
    for step in sys.argv[1:]:
        code = steps[step]() or 0
    sys.exit(code)
