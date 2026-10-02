#!/usr/bin/env python3
"""Probe one TCP target and record its own execution.

Writes two JSON lines per check to --record: one on start, one on finish with
a result. The record is written by the probe itself, never by whatever invoked
it. A caller's output is a claim about what it believes happened; the probe's
output is a trace of what did. Only the trace can distinguish "I probed and it
was refused" from "I never probed".

Exit codes: 0 allowed, 2 refused, 3 timeout, 4 usage error.
"""
import argparse
import json
import socket
import sys
from pathlib import Path


def record(path, check_id, phase, **fields):
    with open(path, "a") as f:
        f.write(json.dumps({"check_id": check_id, "phase": phase, **fields},
                           sort_keys=True) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-id", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--record", required=True)
    # 5s, not 2s: the silent target is the only timing-dependent fixture
    # here, and Docker cold start on a loaded machine could flake it.
    ap.add_argument("--timeout", type=float, default=5.0)
    a = ap.parse_args()

    Path(a.record).parent.mkdir(parents=True, exist_ok=True)
    record(a.record, a.check_id, "start")

    try:
        with socket.create_connection((a.host, a.port), timeout=a.timeout) as s:
            s.sendall(b"PING\n")
            s.settimeout(a.timeout)
            try:
                data = s.recv(32)
            except socket.timeout:
                record(a.record, a.check_id, "end", result="timeout")
                return 3
    except ConnectionRefusedError:
        record(a.record, a.check_id, "end", result="refused")
        return 2
    except (socket.timeout, OSError):
        record(a.record, a.check_id, "end", result="timeout")
        return 3

    if data:
        record(a.record, a.check_id, "end", result="allowed")
        return 0
    # Peer closed without answering: no evidence the service is reachable.
    record(a.record, a.check_id, "end", result="timeout")
    return 3


if __name__ == "__main__":
    sys.exit(main())
