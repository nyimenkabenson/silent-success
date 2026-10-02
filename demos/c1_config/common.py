"""Shared steps for the class 1 demos: clean slate, build inputs, run Suricata.

Everything runs from the repo root using relative paths, so results.json
comes out identical on any machine running the same pinned image.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "jasonish/suricata:7.0.8"
HERE = Path("demos/c1_config")
OUT = Path("out/c1")
PCAP = OUT / "demo.pcap"
CONFIG = OUT / "suricata.yaml"
RULES = HERE / "demo.rules"


def prepare():
    """Start from a clean slate, then build the traffic and config fresh."""
    os.chdir(ROOT)
    if OUT.exists():
        shutil.rmtree(OUT)  # class 6: never inherit a previous run's output
    for script in ("make_pcap.py", "make_config.py"):
        subprocess.run([sys.executable, str(HERE / script)], check=True)


def run_suricata(name, with_config, as_host_user=False):
    """Run real Suricata on the demo traffic. Returns (exit_code, log_dir).

    as_host_user adds --user, which leaves the container unable to read the
    engine's own configuration files. That is a deliberate misconfiguration
    for the third scenario, in the same way omitting -c is for the first.
    """
    log_dir = OUT / name
    log_dir.mkdir(parents=True)
    cmd = ["docker", "run", "--rm"]
    if as_host_user:
        cmd += ["--user", f"{os.getuid()}:{os.getgid()}"]
    cmd += ["-v", f"{ROOT}:/work", "-w", "/work", IMAGE]
    if with_config:
        cmd += ["-c", str(CONFIG)]
    cmd += ["-r", str(PCAP), "-S", str(RULES), "-l", str(log_dir)]
    # Merge stderr into stdout so console.txt preserves the real interleaving:
    # captured separately, the errors would be reordered - a class 4 failure
    # in our own evidence.
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, timeout=180)
    # Suricata may print errors to the console, but a pipeline only reads the
    # exit code. Keep the console output as evidence of exactly that gap.
    (log_dir / "console.txt").write_text(proc.stdout)
    return proc.returncode, log_dir


def count_alerts(eve_path):
    """Alert events in eve.json, or None if there is no eve.json at all."""
    eve_path = Path(eve_path)
    if not eve_path.is_file():
        return None
    lines = eve_path.read_text().splitlines()
    return sum(1 for l in lines if l.strip() and json.loads(l).get("event_type") == "alert")
