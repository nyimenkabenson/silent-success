"""Class 4 guard - evidence doesn't match reality.

Principle: evidence is bound to reality only when checked against an
expectation that does not come from the thing being checked. A hash proves
the files you know about are intact; it cannot prove you know about all of
them. Absence has no hash.
"""
from pathlib import Path

from guards.verdict import Outcome, Verdict

GUARD = "c4.manifest_covers_expected"


def read_expected(path):
    lines = Path(path).read_text().splitlines()
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def read_manifest(path):
    """Parse 'digest  name' lines. Returns (names, error) - error is None if OK."""
    names = []
    for n, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            return None, f"manifest line {n} is not 'sha256  name'"
        names.append(parts[1].strip())
    return names, None


def check_manifest_covers_expected(expected_path, manifest_path):
    expected_path, manifest_path = Path(expected_path), Path(manifest_path)
    evidence = {"expected_file": str(expected_path), "manifest_file": str(manifest_path)}

    def cannot(reason):
        return Verdict(GUARD, Outcome.CANNOT_EVALUATE, reason, evidence)

    if not expected_path.is_file():
        return cannot("expectation file not found; nothing to check the manifest against")
    expected = read_expected(expected_path)
    evidence["expected_count"] = len(expected)
    if not expected:
        return cannot("expectation file lists no artefacts, so a manifest cannot be verified")
    if len(set(expected)) != len(expected):
        return cannot("expectation file lists a name more than once")

    if not manifest_path.is_file():
        return cannot("manifest not found")
    names, error = read_manifest(manifest_path)
    if error:
        return cannot(error)
    evidence["manifest_count"] = len(names)
    if len(set(names)) != len(names):
        return cannot("manifest lists a name more than once")

    missing = sorted(set(expected) - set(names))
    unexpected = sorted(set(names) - set(expected))
    evidence.update(missing=missing, unexpected=unexpected)

    if not missing and not unexpected:
        return Verdict(GUARD, Outcome.PASS,
                       f"manifest covers all {len(expected)} expected artefact(s)", evidence)
    parts = []
    if missing:
        parts.append(f"{len(missing)} missing ({', '.join(missing)})")
    if unexpected:
        parts.append(f"{len(unexpected)} unexpected ({', '.join(unexpected)})")
    return Verdict(GUARD, Outcome.FAIL, "; ".join(parts), evidence)
