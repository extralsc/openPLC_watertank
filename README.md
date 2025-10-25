# openPLC_watertank

# 💧 Water Tank Smart Supervisor — SCS600 ht 2025

This project adds an intelligent supervisory layer and secure logging system to an OpenPLC-based water tank.  
The Python script acts as the on-call engineer’s HMI, automating daily operation and collecting clean evidence of safe behavior.

---

## 🧩 Project Overview

- **OpenPLC program:** `WaterTankPump.st`  
  Provides local, safe control logic for the pump (latching start/stop and emergency stop).
- **Python supervisor:** `tank_supervisor.py`  
  Simulates a “day,” automatically starts/stops the pump, logs key events, and ensures safety.
- **Log analyzer:** `summarize_log.py`  
  Reads the log and summarizes pump cycles, safety trips, and overall behavior.
- **Security hardening:** firewall + multi-factor SSH login on the desktop/HMI.

After one simulated “day,” you can open the summary and answer:

> “Did the pump behave as expected?”

---

## ⚙️ System Architecture

| Component | Role | Location |
|------------|------|----------|
| OpenPLC (`WaterTankPump.st`) | Executes pump control & safety interlocks | PLC or OpenPLC Runtime |
| Python Supervisor (`tank_supervisor.py`) | Supervises operation, simulates drain profile, logs events | Desktop / HMI |
| Log Summary (`summarize_log.py`) | Produces readable daily report | Desktop / HMI |
| Firewall + MFA SSH | Protects desktop access | Desktop |

---

## 📦 Requirements

- **OpenPLC Runtime** or compatible PLC.
- **Python 3.9+**
- Install dependencies:
  ```bash
  pip install pymodbus

