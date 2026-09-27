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
    """Describe the output file as it is right now, before anything runs.

    Records the alert count, not the size or a digest. Suricata assigns
    flow_id at runtime, so two replays of the same pcap produce different
    bytes and different lengths: a recorded digest or size would carry that
    non-determinism into every verdict that copied it. The alert count is
    derived from the packets, so it is stable across invocations.
    """
    if not path.exists():
        return {"existed": False}
    alerts = sum(1 for l in path.read_text().splitlines()
                 if l.strip() and json.loads(l).get("event_type") == "alert")
    return {"existed": True, "alerts": alerts}


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

    out.mkdir(parents=True, exist_ok=True)
    if args.clean:
        # Clear Suricata's output only. The verdict and pre-state records are
        # history, not scratch: removing the whole directory would erase an
        # earlier replay's verdict, so a correct pair would keep no evidence
        # that its first replay ever passed.
        for name in ("eve.json", "console.txt", "fast.log", "stats.log", "suricata.log"):
            (out / name).unlink(missing_ok=True)

    state = pre_state(eve)
    # --clean claims to have emptied the slate. Check that claim against the
    # filesystem rather than assuming the removal worked: a read-only mount, a
    # permissions failure, or a re-created file would all leave it false.
    # (An earlier version compared the record against the same exists() call it
    # was derived from, which could never disagree - a check that always passed.)
    if args.clean and state["existed"]:
        print(f"REFUSED: --clean was given but {eve} still exists; the slate is not clean")
        return 1

    # Numbered like the verdicts, so each verdict has its own intact input
    # beside it. A single pre-state.json would be overwritten by the next
    # replay, leaving an earlier verdict pointing at a file that contradicts
    # it - the evidence describing a state that no longer exists.
    # Note: the sequence counts files already present, so deleting one would
    # cause a collision. Harmless here because the demo wipes out/c6 first.
    seq = len(list(out.glob("pre-state-*.json"))) + 1
    pre_state_file = out / f"pre-state-{seq}.json"
    pre_state_file.write_text(
        json.dumps({"run_id": args.run_id, "sequence": seq, "output": str(eve), **state},
                   indent=2, sort_keys=True) + "\n")

    proc = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{ROOT}:/work", "-w", "/work", IMAGE,
         "-c", "out/c1/suricata.yaml", "-r", "out/c1/demo.pcap",
         "-S", str(C1 / "demo.rules"), "-l", str(out)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
    (out / "console.txt").write_text(proc.stdout)

    # Snapshot the output before judging it: the next replay appends to
    # eve.json, so a verdict naming it would, one run later, point at a file
    # that no longer matches. Copy rather than rename - renaming would leave
    # no eve.json for the next replay to append to, and the carryover this
    # demo exists to reproduce would not happen.
    eve_snapshot = out / f"eve-{seq}.json"
    shutil.copy2(eve, eve_snapshot)

    alerts = sum(1 for l in eve_snapshot.read_text().splitlines()
                 if l.strip() and json.loads(l).get("event_type") == "alert")
    print(f"run {args.run_id}: pre-state {'absent' if not state['existed'] else 'present'}, "
          f"exit {proc.returncode}, {alerts} alert(s) in {eve}")

    # Judge each replay as it happens, and keep the verdict. Without this only
    # the final state survives in the directory: a second replay overwrites
    # pre-state.json, and an earlier PASS becomes unreproducible without
    # re-running - the evidence describing a state that no longer exists.
    # Numbered so replays into the same directory cannot overwrite each other.
    verdict = check_output_free_of_prior_runs(
        Path("demos/c6_carryover/expected_alerts.txt"), pre_state_file, eve_snapshot)
    (out / f"verdict-{seq}.json").write_text(
        json.dumps({"run_id": args.run_id, "sequence": seq, **verdict.to_dict()},
                   indent=2, sort_keys=True) + "\n")
    print(f"  guard: {verdict.outcome.value} - {verdict.reason}")
    print(f"  kept:  {out / f'verdict-{seq}.json'}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
