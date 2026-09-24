"""Replay a pcap through Suricata, recording the output's pre-run state.

Suricata's eve.json carries nothing identifying the invocation - timestamps
come from the packets, so two runs of the same command produce byte-identical
events. The wrapper therefore binds what it does own: the state of the output
file immediately before launch.

The record is checked at launch, not merely asserted: if it says the file was
absent and the file is there, the run refuses before Suricata starts. That
makes the claim falsifiable at launch, though not verifiable afterwards - see
docs/limitations.md.

Usage:
    python demos/c6_carryover/replay.py --run-id <id> [--clean]

--clean removes the output directory first, as the protocol requires.
Omitting it is the mistake this demo reproduces.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from guards.c6_carryover import check_output_free_of_prior_runs

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "jasonish/suricata:7.0.8"
C1 = Path("demos/c1_config")


def pre_state(path):
    """Describe the output file as it is right now, before anything runs."""
    if not path.exists():
        return {"existed": False}
    data = path.read_bytes()
    return {"existed": True, "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True,
                    help="identifier for this run; supply your own to know it is fresh")
    ap.add_argument("--clean", action="store_true",
                    help="remove the output directory first, as the protocol requires")
    args = ap.parse_args()

    import os, shutil
    os.chdir(ROOT)
    out = Path("out/c6") / args.run_id
    eve = out / "eve.json"

    if args.clean:
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    state = pre_state(eve)
    # --clean claims to have emptied the slate. Check that claim against the
    # filesystem rather than assuming the removal worked: a read-only mount, a
    # permissions failure, or a re-created file would all leave it false.
    # (An earlier version compared the record against the same exists() call it
    # was derived from, which could never disagree - a check that always passed.)
    if args.clean and state["existed"]:
        print(f"REFUSED: --clean was given but {eve} still exists; the slate is not clean")
        return 1

    (out / "pre-state.json").write_text(
        json.dumps({"run_id": args.run_id, "output": str(eve), **state},
                   indent=2, sort_keys=True) + "\n")

    proc = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{ROOT}:/work", "-w", "/work", IMAGE,
         "-c", "out/c1/suricata.yaml", "-r", "out/c1/demo.pcap",
         "-S", str(C1 / "demo.rules"), "-l", str(out)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
    (out / "console.txt").write_text(proc.stdout)

    alerts = sum(1 for l in eve.read_text().splitlines()
                 if l.strip() and json.loads(l).get("event_type") == "alert")
    print(f"run {args.run_id}: pre-state {'absent' if not state['existed'] else 'present'}, "
          f"exit {proc.returncode}, {alerts} alert(s) in {eve}")

    # Judge each replay as it happens, and keep the verdict. Without this only
    # the final state survives in the directory: a second replay overwrites
    # pre-state.json, and an earlier PASS becomes unreproducible without
    # re-running - the evidence describing a state that no longer exists.
    # Numbered so replays into the same directory cannot overwrite each other.
    verdict = check_output_free_of_prior_runs(
        Path("demos/c6_carryover/expected_alerts.txt"), out / "pre-state.json", eve)
    seq = len(list(out.glob("verdict-*.json"))) + 1
    (out / f"verdict-{seq}.json").write_text(
        json.dumps({"run_id": args.run_id, "sequence": seq, **verdict.to_dict()},
                   indent=2, sort_keys=True) + "\n")
    print(f"  guard: {verdict.outcome.value} - {verdict.reason}")
    print(f"  kept:  {out / f'verdict-{seq}.json'}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
