# openPLC_watertank


## 🧩 Project Overview

- **OpenPLC program:** `WaterTankPump.st`
  Provides local, safe control logic for the pump (latching start/stop and emergency stop).
- **Python supervisor:** `tank_supervisor.py`
  Simulates a "day," automatically starts/stops the pump, logs key events, and ensures safety.
- **Log analyzer:** `summarize_log.py`
  Reads the log and summarizes pump cycles, safety trips, and overall behavior.
- **Security hardening:** firewall + multi-factor SSH login on the desktop/HMI.

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

- **OpenPLC Runtime** or compatible PLC
- **Python 3.9+**
- **mbpoll** (for manual Modbus testing)
- Install Python dependencies:
  ```bash
  pip install pymodbus
  ```

---

## 🚀 Quick Start

### 1. Configure PLC IP Address

Edit `tank_supervisor.py` line 27 with OpenPLC server IP:
```python
PLC_IP = "193.10.236.xx"  # Replace with actual server IP
```

### 2. Upload PLC Program

1. Open OpenPLC web interface
2. Upload `WaterTankPump.st`
3. Compile and start the runtime
4. Verify Modbus/TCP is enabled on port 502

### 3. Run the Simulation

```bash
# Start the supervisor (runs for 3 hours = 24 simulated hours)
python3 tank_supervisor.py
```

**What happens:**
- Tank starts at 95% level
- Drains according to time-of-day:
  - 00:00-11:59 (sim): 1% every 10 minutes (slow)
  - 12:00-23:59 (sim): 1% every 5 minutes (fast)
- Pump auto-starts when level < 60%
- Pump auto-stops when level ≥ 95%
- All events logged to `tank_events.log`

### 4. Monitor Progress (Optional)

In another terminal:
```bash
# Watch the log in real-time
tail -f tank_events.log
```

Expected log entries:
```
2025-01-23 14:30:15 INFO SUPERVISOR_START
2025-01-23 14:45:22 INFO PUMP_START at 20.0% (sim 01:34:00 simLvl 20.0%)
2025-01-23 15:10:45 INFO PUMP_STOP at 95.1% (sim 03:12:00 simLvl 95.3%)
```

### 5. Analyze Results

After the simulation completes (or press Ctrl+C):

```bash
python3 summarize_log.py
```

**Expected output:**
```
=== Pump Activity Summary ===
Pump starts: 5
  2025-01-23 14:45:22  INFO PUMP_START at 20.0% ...
  ...

Pump stops: 5
  2025-01-23 15:10:45  INFO PUMP_STOP at 95.1% ...
  ...

Safety trips: 1 (if tested)
  2025-01-23 15:05:00  WARNING SAFETY_HIGH_HIGH ...

Approx pump activity window: 2:45:30

Did the pump behave as expected?
  No safety trips. Pump cycled normally between thresholds.
```

---

## 🧪 Testing Safety Features

### Test the Tank_Full Emergency Stop

While the pump is running, trigger the safety sensor:

```bash
# Trigger Tank_Full sensor (coil 803 = 1)
mbpoll -m tcp -a 1 -t 0 -r 803 193.10.236.xx 1

# Check the log immediately
tail -5 tank_events.log
```

**Expected log entry:**
```
2025-01-23 15:05:00 WARNING SAFETY_HIGH_HIGH Tank_Full=1 -> Pump STOP immediately
```

**Clear the condition:**
```bash
# Reset Tank_Full sensor (coil 803 = 0)
mbpoll -m tcp -a 1 -t 0 -r 803 193.10.236.xx 0
```

The pump should restart automatically when the level drops below 60% again.

---

## 📝 Key System Behaviors

| Time (sim) | Drain Rate | Expected Behavior |
|------------|------------|-------------------|
| 00:00-11:59 | 1% / 10 min | Slow drain, pump starts occasionally |
| 12:00-23:59 | 1% / 5 min | Fast drain, pump cycles more frequently |
| Any time | Tank_Full=1 | Pump stops immediately (safety override) |

**Control thresholds:**
- Start pump: level < 60%
- Stop pump: level ≥ 95%

---

## 📋 Logging System

The supervisor uses Python's `RotatingFileHandler` to maintain clean, manageable logs:

**Log rotation behavior:**
- **Primary log:** `tank_events.log` (current events)
- **Max file size:** 2 GiB per file
- **Backup count:** 3 rotated files
- **Total storage:** Up to 4 log files (~8 GiB max)

When `tank_events.log` reaches 2 GiB:
1. `tank_events.log` → `tank_events.log.1`
2. `tank_events.log.1` → `tank_events.log.2`
3. `tank_events.log.2` → `tank_events.log.3`
4. `tank_events.log.3` is deleted
5. Fresh `tank_events.log` created

**What gets logged:**
- ✅ Pump starts/stops with timestamp and level
- ✅ Safety trips (Tank_Full emergency stop)
- ✅ Supervisor lifecycle events (start/stop)
- ❌ No routine polling data (keeps logs readable)

**View logs:**
```bash
# Latest events
tail -f tank_events.log

# All pump activity
grep "PUMP_" tank_events.log

# Safety events only
grep "SAFETY" tank_events.log
```

**Analyze logs:**

The `summarize_log.py` script reads `tank_events.log` and generates a summary report:

```bash
python3 summarize_log.py
```

**Output includes:**
- Total pump starts and stops with timestamps
- Safety trip events (if any)
- Total pump active time
- Behavioral assessment ("Did the pump behave as expected?")

This is the primary tool for verifying system operation and generating evidence reports.

---


### Critical files

- `tank_supervisor.py` (the control script)
- `summarize_log.py` (log analyzer)
- `WaterTankPump.st` (PLC program)
- `tank_events.log` (or excerpt showing key events)

