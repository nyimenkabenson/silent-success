"""Build the class 1 demo config: the pinned image's default suricata.yaml
plus exactly one added line defining DEMO_NET.

Generated rather than committed, so it always matches the pinned image and
the only thing this project authors is the single added line.
"""
import re
import subprocess
from pathlib import Path

IMAGE = "jasonish/suricata:7.0.8"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "c1" / "suricata.yaml"
ADDED = '    DEMO_NET: "[10.99.0.0/24]"\n'

default = subprocess.run(
    ["docker", "run", "--rm", "--entrypoint", "cat", IMAGE,
     "/etc/suricata/suricata.yaml"],
    check=True, capture_output=True, text=True,
).stdout

hits = re.findall(r"^    HOME_NET: .*\n", default, flags=re.M)
if len(hits) != 1:
    raise SystemExit(f"expected exactly one HOME_NET line, found {len(hits)}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(default.replace(hits[0], hits[0] + ADDED, 1))
print(f"default config: {len(default.splitlines())} lines")
print(f"anchor: {hits[0].strip()}")
print(f"wrote {OUT} ({len(OUT.read_text().splitlines())} lines)")
