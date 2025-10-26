#!/usr/bin/env python3
"""
tank_supervisor.py
Supervisory controller / HMI brain for the water tank.

Features:
- Simulated "day" timeline (00:00-23:59) compressed into ACCELERATED_DAY_SECONDS.
- Morning slow drain, afternoon fast drain, per requirements.
- Auto start/stop pump with thresholds.
- Emergency stop if Tank_Full.
- Clean event logging with rotation <=2 GiB.
- This log is later summarized by summarize_log.py.

Requires: pip install pymodbus
"""

import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from pymodbus.client import ModbusTcpClient

# -----------------------------
# CONFIG
# -----------------------------

PLC_IP   = "193.10.236.xx"  # <-- set to your PLC IP
PLC_PORT = 502              # Modbus/TCP default

COIL_PUMP_STATUS = 0        # coil 1 in mbpoll = coil 0 in pymodbus
COIL_START       = 800      # coil 801 in mbpoll = coil 800 in pymodbus
COIL_STOP        = 801      # coil 802 in mbpoll = coil 801 in pymodbus
COIL_FULL        = 802      # coil 803 in mbpoll = coil 802 in pymodbus
REG_LEVEL        = 0        # holding reg 40001: tank level %

LOW_THRESHOLD = 60.0        # start pump below this
STOP_TARGET   = 95.0        # stop pump above this
PULSE_SEC     = 1.0         # press button duration
SCAN_SEC      = 2.0         # main loop cycle time

# Simulated "day" compression:
ACCELERATED_DAY_SECONDS = 3 * 60 * 60  # 24h sim in 3h real (adjust if you want)
SECONDS_PER_SIM_MINUTE  = ACCELERATED_DAY_SECONDS / (24 * 60)

# Logging / rotation
logger = logging.getLogger("tank")
handler = RotatingFileHandler(
    "tank_events.log",
    maxBytes = 2 * 1024 * 1024 * 1024,  # 2 GiB
    backupCount = 3
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s",
    "%Y-%m-%d %H:%M:%S"
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -----------------------------
# Utility funcs
# -----------------------------


def read_level(client):
    rr = client.read_holding_registers(REG_LEVEL, 1)
    if rr.isError():
        return None
    return float(rr.registers[0])

def write_level(client, level_pct):
    """Write the tank level percentage to the PLC holding register."""
    client.write_register(REG_LEVEL, int(level_pct))

def read_coil(client, addr):
    rr = client.read_coils(addr, 1)
    if rr.isError():
        return None
    return bool(rr.bits[0])

# -----------------------------
# Day simulator for drain profile
# -----------------------------

class DaySim:
    """
    Tracks simulated time-of-day and calculates tank level based on drain profile.
    The calculated level is written to the PLC to simulate realistic consumption.
    """
    def __init__(self, initial_level=95.0):
        self.real_t0 = time.time()
        self.sim_t0  = datetime(2000,1,1,0,0,0)
        self.last_real = self.real_t0
        self.level = initial_level
        self.pump_expected_running = False

    def sim_now(self):
        real_elapsed = time.time() - self.real_t0
        sim_minutes  = real_elapsed / SECONDS_PER_SIM_MINUTE
        return self.sim_t0 + timedelta(minutes=sim_minutes)

    def update(self):
        now_real = time.time()
        dt_real = now_real - self.last_real
        self.last_real = now_real

        sim_time = self.sim_now()

        # Drain rate logic:
        # 00:00 - 11:59  -> 1% every 10 sim minutes = 0.1 %/sim_min
        # 12:00 - 23:59  -> 1% every 5 sim minutes  = 0.2 %/sim_min
        if sim_time.hour < 12:
            pct_per_sim_minute = 0.1
        else:
            pct_per_sim_minute = 0.2

        # Convert %/sim_min to %/real_sec:
        #  pct_per_sim_min / (60 sim_sec / SECONDS_PER_SIM_MINUTE real_sec)
        drain_per_real_sec = pct_per_sim_minute / (60.0 / SECONDS_PER_SIM_MINUTE)

        dlevel = -drain_per_real_sec * dt_real

        # Rough fill model if pump_expected_running:
        # assume +1% per sim minute
        fill_pct_per_real_sec = (1.0 / (60.0 / SECONDS_PER_SIM_MINUTE))
        if self.pump_expected_running:
            dlevel += fill_pct_per_real_sec * dt_real

        self.level += dlevel
        if self.level < 0.0: self.level = 0.0
        if self.level > 100.0: self.level = 100.0

        return sim_time, self.level

# -----------------------------
# Main
# -----------------------------

def main():
    client = ModbusTcpClient(PLC_IP, PLC_PORT)
    if not client.connect():
        print("ERROR: Could not connect to PLC")
        return

    logger.info("SUPERVISOR_START")

    sim = DaySim(initial_level=20.0)

    # Sync with actual PLC state at startup
    pump_status = read_coil(client, COIL_PUMP_STATUS)
    pump_on_cmd_state = bool(pump_status) if pump_status is not None else False

    if pump_status:
        logger.info(f"SYNC: Found pump already running on startup")
        sim.pump_expected_running = True
    else:
        sim.pump_expected_running = False

    try:
        while True:
            # Advance simulation model
            sim_time, sim_level = sim.update()

            # Write simulated drain to PLC
            write_level(client, sim_level)

            # Read plant
            tank_level = read_level(client)
            tank_full  = read_coil(client, COIL_FULL)
            pump_actual = read_coil(client, COIL_PUMP_STATUS)

            # Emergency override first
            if tank_full:
                client.write_coil(COIL_STOP, True)
                time.sleep(0.5)
                client.write_coil(COIL_STOP, False)
                sim.pump_expected_running = False
                pump_on_cmd_state = False
                logger.warning("SAFETY_HIGH_HIGH Tank_Full=1 -> Pump STOP immediately")

            else:
                # Normal control band
                if tank_level is not None:
                    # Need pump?
                    if (tank_level < LOW_THRESHOLD) and (pump_on_cmd_state is False):
                        client.write_coil(COIL_START, True)
                        time.sleep(0.5)
                        client.write_coil(COIL_START, False)
                        pump_on_cmd_state = True
                        sim.pump_expected_running = True
                        logger.info(f"PUMP_START at {tank_level:.1f}% (sim {sim_time.time()} simLvl {sim_level:.1f}%)")

                    # Stop condition near 95%
                    if (tank_level >= STOP_TARGET) and (pump_on_cmd_state is True):
                        client.write_coil(COIL_STOP, True)
                        time.sleep(0.5)
                        client.write_coil(COIL_STOP, False)  # Clear stop button
                        pump_on_cmd_state = False
                        sim.pump_expected_running = False
                        logger.info(f"PUMP_STOP at {tank_level:.1f}% (sim {sim_time.time()} simLvl {sim_level:.1f}%)")

            # (Optional debug: not INFO, so it won't flood log)
            # logger.debug(
            #     f"heartbeat sim={sim_time.time()} simLvl={sim_level:.1f}% "
            #     f"tank={tank_level} pump_actual={pump_actual} full={tank_full}"
            # )

            time.sleep(SCAN_SEC)

    except KeyboardInterrupt:
        logger.info("SUPERVISOR_STOP (KeyboardInterrupt)")
    finally:
        client.close()

if __name__ == "__main__":
    main()

