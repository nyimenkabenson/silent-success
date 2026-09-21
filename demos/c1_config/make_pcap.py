"""Build the class 1 demo traffic: one ICMP echo request from the demo network.

Everything is fixed - addresses, payload, timestamp - so this produces
byte-identical output on every run and every machine.
"""
from pathlib import Path

from scapy.all import ICMP, IP, Ether, Raw, wrpcap

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "c1" / "demo.pcap"

pkt = (
    Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
    / IP(src="10.99.0.5", dst="10.99.0.9")
    / ICMP(type=8, id=1, seq=1)
    / Raw(b"silent-success-class1")
)
pkt.time = 1767225600  # 2026-01-01T00:00:00Z, fixed for determinism

OUT.parent.mkdir(parents=True, exist_ok=True)
wrpcap(str(OUT), [pkt])
print(f"repo root: {ROOT}")
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
