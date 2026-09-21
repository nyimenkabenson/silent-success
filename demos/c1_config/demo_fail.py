"""Class 1 - demo_fail: Suricata reports success while detecting nothing.

Runs real Suricata with the rules passed but the config left out, then shows
exactly what an automated pipeline sees. Exits 0 if the failure reproduced.
"""
import sys

import common


def main():
    common.prepare()
    code, log_dir = common.run_suricata("broken", with_config=False)
    alerts = common.count_alerts(log_dir / "eve.json")
    clean = code == 0 and alerts == 0

    print("\nWhat the pipeline sees")
    print(f"  suricata exit code : {code}")
    print(f"  alerts             : {alerts}")
    print(f"  pipeline verdict   : {'CLEAN' if clean else 'NOT CLEAN'}")
    print(f"\nSuricata's console output is kept in {log_dir / 'console.txt'}")

    if clean:
        print("\nREPRODUCED: exit 0, zero alerts. "
              "Run demo_catch.py to see how many rules actually loaded.")
        return 0
    print("\nNOT REPRODUCED: Suricata did not report a clean run here.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
