"""The naive checker: asks whether traffic to a target is allowed, by running a
probe and reading its exit code.

This is the component that lies, and it is written the way such a component is
ordinarily written: run the probe, treat a clean exit as allowed and anything
else as denied. The rule is not careless - a refusal really does exit nonzero -
it is just incapable of distinguishing a refusal from a probe that never ran.
Exit 2 (refused) and exit 127 (command not found) both become "deny".

The checker never reads the probe's record. That separation is the point: the
checker's output is its claim, the probe's record is the trace, and the guard
judges one against the other.

The targets are ports on localhost inside the container, not firewall rules.
The demo is about verdict provenance, not firewall realism - the mechanism is
simplified for reproducibility, the same way class 1 omits -c rather than
staging a real misconfiguration.
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# check_id -> port inside the container
CHECKS = {"CHK-ALLOW": 9001, "CHK-REFUSED": 9002, "CHK-SILENT": 9003}


def start_targets(image, container):
    subprocess.run(["docker", "rm", "-f", container],
                   capture_output=True, text=True)
    subprocess.run(
        # The probe is plain Python binding unprivileged ports; it has no
        # reason to run as root, and a root-owned record in the bind mount
        # cannot be removed or rewritten by the next run.
        ["docker", "run", "-d", "--name", container,
         "--user", f"{os.getuid()}:{os.getgid()}",
         "-v", f"{ROOT}:/work", "-w", "/work", image],
        check=True, capture_output=True, text=True)
    # Wait for the listeners rather than sleeping a fixed amount.
    for _ in range(50):
        logs = subprocess.run(["docker", "logs", container],
                              capture_output=True, text=True).stdout
        if "targets up" in logs:
            return
        subprocess.run(["sleep", "0.2"])
    raise SystemExit(f"{container}: targets did not come up")


def stop(container):
    subprocess.run(["docker", "rm", "-f", container], capture_output=True, text=True)


def run_check(container, check_id, record_rel):
    """Run one probe. Returns (exit_code, verdict) under the naive rule."""
    proc = subprocess.run(
        ["docker", "exec", "--user", f"{os.getuid()}:{os.getgid()}",
         container, "probe",
         "--check-id", check_id, "--port", str(CHECKS[check_id]),
         "--record", f"/work/{record_rel}"],
        capture_output=True, text=True, timeout=60)
    verdict = "allow" if proc.returncode == 0 else "deny"
    return proc.returncode, verdict


def check_all(container, check_ids, record_rel, out_path):
    verdicts = []
    for check_id in check_ids:
        code, verdict = run_check(container, check_id, record_rel)
        verdicts.append({"check_id": check_id, "exit_code": code, "verdict": verdict})
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(verdicts, indent=2, sort_keys=True) + "\n")
    return verdicts
