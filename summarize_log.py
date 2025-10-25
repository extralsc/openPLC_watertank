#!/usr/bin/env python3
"""
summarize_log.py
Parses tank_events.log and prints a human summary:
- when pump started
- when pump stopped
- any safety trips
"""

import re
from datetime import datetime

LOGFILE = "tank_events.log"

RE_START   = re.compile(r"PUMP_START")
RE_STOP    = re.compile(r"PUMP_STOP")
RE_SAFETY  = re.compile(r"SAFETY_HIGH_HIGH")

def ts_from_line(line):
    # log format: "YYYY-mm-dd HH:MM:SS LEVEL ..."
    ts = " ".join(line.split(" ", 2)[:2])
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

def main():
    starts = []
    stops  = []
    safeties = []

    with open(LOGFILE) as f:
        for line in f:
            if RE_START.search(line):
                starts.append((ts_from_line(line), line.strip()))
            if RE_STOP.search(line):
                stops.append((ts_from_line(line), line.strip()))
            if RE_SAFETY.search(line):
                safeties.append((ts_from_line(line), line.strip()))

    print("=== Pump Activity Summary ===")
    print(f"Pump starts: {len(starts)}")
    for ts, msg in starts:
        print(f"  {ts}  {msg}")

    print(f"\nPump stops: {len(stops)}")
    for ts, msg in stops:
        print(f"  {ts}  {msg}")

    print(f"\nSafety trips: {len(safeties)}")
    for ts, msg in safeties:
        print(f"  {ts}  {msg}")

    if starts and stops:
        first_on = min(ts for ts, _ in starts)
        last_off = max(ts for ts, _ in stops)
        print(f"\nApprox pump activity window: {last_off - first_on}")

    print("\nDid the pump behave as expected?")
    if safeties:
        print("  Safety triggered. Check high-level alarm conditions.")
    else:
        print("  No safety trips. Pump cycled normally between thresholds.")

if __name__ == "__main__":
    main()

