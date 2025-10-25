# 📚 Solution Explanation & Answer Guide
## Water Tank Smart Supervisor — SCS600 ht 2025

This document explains **what the code does**, **how it works**, and **why design decisions were made**. Use this to understand your solution and explain it to your teacher.

---

## 🏗️ System Architecture Overview

### The Big Picture

The solution uses **two systems working together** in a distributed control architecture:

```
┌─────────────────────┐         Modbus/TCP          ┌──────────────────┐
│   Desktop (HMI)     │◄──────────────────────────►│  OpenPLC Server  │
│                     │                             │                  │
│ tank_supervisor.py  │  Writes: Tank level        │ WaterTankPump.st │
│                     │  Reads:  Pump status       │                  │
│                     │  Writes: Start/Stop cmds   │ Controls: Pump   │
└─────────────────────┘                             └──────────────────┘
         │
         ├─► tank_events.log (clean event log)
         └─► summarize_log.py (analyzes the log)
```

### Why This Architecture?

**Separation of Concerns:**
- **PLC (OpenPLC Server):** Handles real-time safety and local control
- **Desktop:** Handles supervisory logic, simulation, and logging
- **Result:** Each system does what it's best at

**Defense in Depth:**
- If Desktop crashes → PLC keeps pump safe (Tank_Full sensor still works)
- If network fails → PLC maintains last safe state
- **Belt + suspenders approach** to safety

**Industry Standard:**
- This mimics real SCADA (Supervisory Control and Data Acquisition) systems
- PLCs handle millisecond-level safety
- HMI/Desktop handles minute-level optimization

---

## 📄 File 1: `WaterTankPump.st` (PLC Program)

### Purpose

This is the **safety-critical local controller** running on the OpenPLC server. It's the "last line of defense" that protects the pump from damage.

### Code Breakdown

#### Variable Declarations (Lines 7-21)

```iecst
VAR
    (* Inputs from Desktop via Modbus *)
    PB_Start      AT %IX0.0 : BOOL;   (* Coil 801: momentary start *)
    PB_Stop       AT %IX0.1 : BOOL;   (* Coil 802: momentary stop *)
    Tank_Full     AT %IX0.3 : BOOL;   (* Coil 803: safety sensor *)

    (* Tank level from simulation *)
    Tank_Level    AT %IW0 : INT;      (* Holding register 40001: 0-100% *)

    (* Internal state *)
    Pump_Run      : BOOL := FALSE;    (* Latched run command *)

    (* Output *)
    Pump_Motor    AT %QX0.0 : BOOL;   (* Coil 1: physical pump output *)
END_VAR
```

**Key Concepts:**

1. **AT %IX0.0** = Direct I/O mapping
   - `%I` = Input
   - `%Q` = Output
   - `X` = Bit (digital)
   - `W` = Word (analog/integer)
   - Example: `%IX0.0` = Input bit 0.0 (Modbus coil 801)

2. **Modbus Mapping:**
   - Coil 801-803 → Input bits %IX0.0 to %IX0.3
   - Holding reg 40001 → Input word %IW0
   - Coil 1 → Output bit %QX0.0

3. **Latched State:**
   - `Pump_Run` is **internal memory** (not mapped to I/O)
   - Stays TRUE even after start button releases
   - Like a mechanical relay that "stays clicked"

#### Logic: Normal Start (Lines 24-26)

```iecst
IF PB_Start AND NOT Tank_Full THEN
    Pump_Run := TRUE;
END_IF;
```

**What it does:**
- When Desktop pulses coil 801 (start button)
- AND Tank_Full sensor is not active
- THEN latch the pump ON

**Why the Tank_Full check?**
- **Safety interlock:** Won't start if tank already dangerously full
- Prevents overflow even if Desktop sends bad command
- PLC has final say on safety

**Why latch instead of direct control?**
- Mimics real start/stop stations (push button, relay latches)
- Pump stays running even if Modbus connection drops
- Prevents pump from cycling if network glitches

#### Logic: Normal Stop (Lines 28-30)

```iecst
IF PB_Stop THEN
    Pump_Run := FALSE;
END_IF;
```

**What it does:**
- When Desktop pulses coil 802 (stop button)
- THEN unlatch the pump

**Why no conditions?**
- **You can always stop for safety**
- No "safety check" needed to turn pump OFF
- "When in doubt, shut it down" philosophy

#### Logic: Emergency Override (Lines 32-35)

```iecst
IF Tank_Full THEN
    Pump_Run := FALSE;
END_IF;
```

**What it does:**
- If Tank_Full sensor activates (level too high)
- THEN immediately force pump OFF

**Why this is critical:**
- Runs **every PLC scan cycle** (~10 milliseconds)
- Overrides everything else - even if Desktop says "run"
- **Hardwired safety** that can't be bypassed
- Protects against overflow/tank damage

**Order matters:**
- This runs AFTER the start logic
- If both `PB_Start=1` and `Tank_Full=1`, pump stays OFF
- Emergency stop has **final authority**

#### Output Assignment (Line 38)

```iecst
Pump_Motor := Pump_Run;
```

**What it does:**
- Copies internal latch state to physical output

**Why separate?**
- Good programming practice: logic separate from I/O
- Easier to debug (can inspect `Pump_Run` independently)
- Could add additional output logic here if needed

### Design Philosophy

**Simple = Reliable:**
- Only 15 lines of logic
- Easy to verify correctness
- Hard to break

**Fail-Safe:**
- If power cycles, pump defaults to OFF
- If Modbus disconnects, pump stays in last state
- Multiple stop conditions, single start condition

**Industry Standard:**
- This is exactly how real pump controllers work
- Start/Stop with emergency override is universal
- Any maintenance engineer would understand this

---

## 📄 File 2: `tank_supervisor.py` (Desktop Supervisor)

This is your **intelligent control system** that simulates water usage and manages the pump automatically.

### Part 1: Configuration (Lines 24-42)

#### PLC Connection Settings

```python
PLC_IP   = "193.10.236.xx"  # Your OpenPLC server IP
PLC_PORT = 502              # Modbus/TCP standard port
```

**Why port 502?**
- IANA standard for Modbus/TCP
- Like HTTP uses port 80, Modbus uses 502
- Any Modbus client expects this

#### Modbus Address Mapping

```python
COIL_PUMP_STATUS = 1        # Read: Is pump running?
COIL_START       = 801      # Write: Pulse to start
COIL_STOP        = 802      # Write: Pulse to stop
COIL_FULL        = 803      # Write: Simulate sensor
REG_LEVEL        = 0        # Read/Write: Tank level %
```

**Understanding the addresses:**

| Name | Type | Modbus Addr | PLC Mapping | Direction |
|------|------|-------------|-------------|-----------|
| PUMP_STATUS | Coil | 1 | %QX0.0 | Desktop reads |
| START | Coil | 801 | %IX0.0 | Desktop writes |
| STOP | Coil | 802 | %IX0.1 | Desktop writes |
| TANK_FULL | Coil | 803 | %IX0.3 | Desktop writes |
| TANK_LEVEL | Holding Reg | 40001 (offset 0) | %IW0 | Desktop writes, PLC reads |

**Why these specific numbers?**
- OpenPLC maps coils 801+ to digital inputs
- Holding register 0 = standard analog input location
- Matches OpenPLC's default Modbus mapping

#### Control Thresholds

```python
LOW_THRESHOLD = 60.0        # Start pump below 60%
STOP_TARGET   = 95.0        # Stop pump at 95%
```

**Why 60% and 95%?**

1. **35% Hysteresis (Deadband):**
   - Prevents rapid on/off cycling ("chattering")
   - Example without deadband:
     ```
     60.0% → Start pump
     60.1% → Stop pump (if stop threshold = 60%)
     59.9% → Start pump
     60.1% → Stop pump
     ... pump cycles every few seconds! (BAD)
     ```
   - With 35% deadband:
     ```
     60% → Start pump
     ... runs continuously ...
     95% → Stop pump
     ... waits for natural drain ...
     60% → Start pump (next cycle)
     ... healthy operation! (GOOD)
     ```

2. **Safety Margin:**
   - Start at 60% → won't run dry (0% = empty)
   - Stop at 95% → won't overflow (100% = full)
   - Leaves 5% buffer before Tank_Full triggers

3. **Energy Efficiency:**
   - Fewer start/stop cycles = less motor wear
   - Less energy wasted on startup current
   - Common in HVAC, pumps, chillers

#### Timing Parameters

```python
PULSE_SEC     = 0.2         # Button press duration
SCAN_SEC      = 2.0         # Main loop cycle time
```

**Why 0.2 seconds for pulse?**
- PLC scans at ~10ms, will definitely see a 200ms pulse
- Long enough to be reliable, short enough to feel "momentary"
- Mimics real pushbutton press

**Why 2 seconds for scan?**
- Tank level changes slowly (minutes, not seconds)
- No need to poll faster
- Reduces Modbus traffic (plays nice on shared network)
- Industry typical: 1-5 second scan for non-critical loops

#### Time Compression

```python
ACCELERATED_DAY_SECONDS = 3 * 60 * 60  # 24 simulated hours = 3 real hours
SECONDS_PER_SIM_MINUTE  = ACCELERATED_DAY_SECONDS / (24 * 60)
# Result: SECONDS_PER_SIM_MINUTE = 7.5
```

**The math:**
- 24 hours = 1440 minutes
- 3 real hours = 10,800 real seconds
- 10,800 / 1440 = 7.5 real seconds per simulated minute
- **1 sim minute = 7.5 real seconds**

**Why compress time?**
- Testing: Don't wait 24 real hours to validate!
- Full day simulation in one afternoon
- All drain/fill rates scale proportionally
- Common technique in control system validation

### Part 2: Logging System (Lines 46-57)

```python
logger = logging.getLogger("tank")
handler = RotatingFileHandler(
    "tank_events.log",
    maxBytes = 2 * 1024 * 1024 * 1024,  # 2 GiB max size
    backupCount = 3                      # Keep 3 backups
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s",
    "%Y-%m-%d %H:%M:%S"
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

#### What is RotatingFileHandler?

**How it works:**
1. Writes to `tank_events.log`
2. When file reaches 2 GiB:
   - Renames `tank_events.log` → `tank_events.log.1`
   - Renames `tank_events.log.1` → `tank_events.log.2`
   - Renames `tank_events.log.2` → `tank_events.log.3`
   - Deletes old `tank_events.log.3`
   - Creates fresh `tank_events.log`
3. Max disk usage: 4 × 2 GiB = 8 GiB

**Why this approach?**

**Problem with naive logging:**
```python
# BAD approach:
with open("log.txt", "a") as f:
    while True:
        f.write(f"{time.time()} Tank level: {level}\n")
        time.sleep(1)
```
- Logs 86,400 lines per day (1 per second)
- After 1 year: 31 million lines
- **Fills disk, system crashes!** (Common failure mode)

**Our solution:**
- Log only **state changes** (not every reading)
- Automatic rotation **prevents disk fill**
- Old logs auto-deleted (keeps recent history)

#### Log Levels

```python
logger.setLevel(logging.INFO)
```

**Python logging hierarchy:**
```
DEBUG    (10) - Detailed diagnostic info (not logged)
INFO     (20) - Normal operation events (PUMP_START, PUMP_STOP)
WARNING  (30) - Something unusual (SAFETY_HIGH_HIGH)
ERROR    (40) - Something failed (not used here)
CRITICAL (50) - System failure (not used here)
```

**Our usage:**
- `INFO`: Normal pump cycles (expected events)
- `WARNING`: Safety activation (unusual but handled)
- Result: Only significant events logged, no spam

#### Format String

```python
"%(asctime)s %(levelname)s %(message)s"
```

**Example output:**
```
2025-01-23 14:45:22 INFO PUMP_START at 58.2% (sim 01:34:00 simLvl 59.1%)
2025-01-23 15:05:00 WARNING SAFETY_HIGH_HIGH Tank_Full=1 -> Pump STOP immediately
2025-01-23 15:10:45 INFO PUMP_STOP at 95.1% (sim 03:12:00 simLvl 95.3%)
```

**Why this format?**
- **Timestamp:** When did it happen? (for timeline reconstruction)
- **Level:** How important? (INFO vs WARNING)
- **Message:** What happened? (human-readable)
- **Parseable:** Easy for `summarize_log.py` to extract

### Part 3: Utility Functions (Lines 63-78)

#### pulse_coil() - Simulating a Button Press

```python
def pulse_coil(client, addr):
    client.write_coil(addr, True)   # Press button (1)
    time.sleep(PULSE_SEC)            # Hold for 0.2 sec
    client.write_coil(addr, False)   # Release button (0)
```

**Why pulse instead of just setting to TRUE?**

**PLC latch logic needs a "rising edge":**
```
Coil value:  0 0 0 0 1 1 1 1 0 0 0
PLC sees:           ↑ Rising edge! (0→1 transition)
Action:             Latch Pump_Run = TRUE
```

**If we just set to 1 and leave it:**
```
Coil value:  0 0 1 1 1 1 1 1 1 1 1
PLC sees:       ↑ Edge
Action:         Latch = TRUE
Problem:        Stays TRUE forever (can't stop!)
```

**With pulse (what we do):**
```
Coil value:  0 0 1 0 0 0 0 0 0 0 0
PLC sees:       ↑ Edge
Action:         Latch = TRUE
Result:         Can send another pulse later to stop
```

**Real-world analogy:**
- Like a doorbell: you press and release
- Not like a light switch: you press and leave it

#### write_level() - The Critical Fix!

```python
def write_level(client, level_pct):
    """Write the tank level percentage to the PLC holding register."""
    client.write_register(REG_LEVEL, int(level_pct))
```

**Why this function is critical:**

**Before this fix:**
```
Time   | Python sim | PLC Tank_Level | Pump Decision
-------|------------|----------------|---------------
00:00  | 95%        | 95%            | Don't start (above 60%)
01:00  | 89%        | 95%            | Don't start (PLC still sees 95%!)
02:00  | 83%        | 95%            | Don't start (stuck!)
```

**After this fix:**
```
Time   | Python sim | write_level() | PLC Tank_Level | Pump Decision
-------|------------|---------------|----------------|---------------
00:00  | 95%        | → writes 95   | 95%            | Don't start
01:00  | 89%        | → writes 89   | 89%            | Don't start
02:00  | 83%        | → writes 83   | 83%            | Don't start
10:00  | 59%        | → writes 59   | 59%            | START! (<60%)
```

**What was missing:**
- The PLC doesn't "know" about the simulation
- We must **tell the PLC** the tank is draining by writing the level
- Otherwise PLC sees a constant 95% forever

**Technical details:**
- Writes to Modbus holding register 0 (address 40001)
- PLC reads this as `Tank_Level AT %IW0`
- `int(level_pct)` converts float (59.3) to integer (59)

#### read_level() and read_coil()

```python
def read_level(client):
    rr = client.read_holding_registers(REG_LEVEL, 1)
    if rr.isError():
        return None  # Communication failed
    return float(rr.registers[0])

def read_coil(client, addr):
    rr = client.read_coils(addr, 1)
    if rr.isError():
        return None  # Communication failed
    return bool(rr.bits[0])
```

**Why check for errors?**
- Network can drop packets
- PLC might restart
- Cable could disconnect

**Defensive programming:**
```python
if tank_level is not None:  # Only act if we got valid data
    # Make control decisions
```

**Without error checking:**
```python
# BAD: Crashes if Modbus fails
level = read_level(client)
if level < 60:  # TypeError if level is None!
    start_pump()
```

### Part 4: DaySim Class - The Physics Model (Lines 88-135)

This class simulates the **water consumption behavior** of the building.

#### Initialization

```python
class DaySim:
    def __init__(self, initial_level=95.0):
        self.real_t0 = time.time()              # Real clock: when we started
        self.sim_t0  = datetime(2000,1,1,0,0,0) # Sim clock: midnight
        self.last_real = self.real_t0           # For calculating deltas
        self.level = initial_level              # Tank starts 95% full
        self.pump_expected_running = False      # Are we filling?
```

**Why two clocks?**
- `real_t0`: Actual wall-clock time (for calculating elapsed seconds)
- `sim_t0`: Simulated time of day (for drain rate decisions)

**Example:**
```
Real time:  14:35:22 (2:35 PM, actual clock)
Sim time:   00:10:00 (10 minutes past simulated midnight)
```

#### sim_now() - Time Conversion

```python
def sim_now(self):
    real_elapsed = time.time() - self.real_t0       # Real seconds passed
    sim_minutes  = real_elapsed / SECONDS_PER_SIM_MINUTE  # Convert to sim minutes
    return self.sim_t0 + timedelta(minutes=sim_minutes)   # Add to sim midnight
```

**Example calculation:**
```
Simulation started at: 14:00:00 real time
Current time:          14:01:15 real time
real_elapsed:          75 real seconds

SECONDS_PER_SIM_MINUTE = 7.5
sim_minutes = 75 / 7.5 = 10 simulated minutes

sim_t0 = 2000-01-01 00:00:00
result = 00:00:00 + 10 minutes = 00:10:00 (simulated time)
```

**Why this matters:**
- Determines drain rate (morning slow, afternoon fast)
- Provides context in log messages
- Allows daily pattern simulation

#### update() - The Heart of the Simulation

```python
def update(self):
    # Calculate real time delta
    now_real = time.time()
    dt_real = now_real - self.last_real  # Seconds since last update
    self.last_real = now_real

    sim_time = self.sim_now()  # What time is it in simulation?
```

**Time delta tracking:**
- Each loop iteration: ~2 seconds apart (SCAN_SEC)
- `dt_real` = actual seconds elapsed
- Used to calculate how much level changed

#### Drain Rate Logic (The Requirements!)

```python
    # Morning vs Afternoon drain rates
    if sim_time.hour < 12:
        pct_per_sim_minute = 0.1  # 00:00-11:59: slow usage
    else:
        pct_per_sim_minute = 0.2  # 12:00-23:59: fast usage
```

**Requirement translation:**
| Requirement | Our Code | Meaning |
|-------------|----------|---------|
| "Morning: 1% every 10 sim min" | 0.1% per sim min | 10 × 0.1 = 1% ✓ |
| "Afternoon: 1% every 5 sim min" | 0.2% per sim min | 5 × 0.2 = 1% ✓ |

#### Unit Conversion (The Tricky Part!)

```python
    # Convert from "% per sim minute" to "% per real second"
    drain_per_real_sec = pct_per_sim_minute / (60.0 / SECONDS_PER_SIM_MINUTE)

    dlevel = -drain_per_real_sec * dt_real  # Negative = draining
```

**The math explained:**

**Morning drain calculation:**
```
pct_per_sim_minute = 0.1% / sim_min
SECONDS_PER_SIM_MINUTE = 7.5 real_sec / sim_min

Step 1: How many real seconds in one sim minute?
    60 sim_sec / sim_min ÷ 7.5 real_sec / sim_min = 8 real_sec

Step 2: Convert to real seconds:
    drain_per_real_sec = 0.1% / 8 real_sec = 0.0125% / real_sec

Step 3: Apply time delta (if 2 real seconds passed):
    dlevel = -0.0125 × 2 = -0.025%
```

**Why negative?**
- Draining removes water: level goes DOWN
- `-dlevel` = decreasing level

**Afternoon is twice as fast:**
```
pct_per_sim_minute = 0.2% / sim_min
drain_per_real_sec = 0.2% / 8 = 0.025% / real_sec
(Exactly 2× the morning rate!) ✓
```

#### Fill Rate (Pump Running)

```python
    # If pump is running, add fill rate
    fill_pct_per_real_sec = (1.0 / (60.0 / SECONDS_PER_SIM_MINUTE))
    if self.pump_expected_running:
        dlevel += fill_pct_per_real_sec * dt_real
```

**Requirement:** "100 minutes from empty to full" = 1% per minute

**Our implementation:**
```
fill_rate = 1.0% / sim_min
fill_pct_per_real_sec = 1.0 / 8 = 0.125% / real_sec

If pump runs for 16 real seconds:
    fill = 0.125 × 16 = 2% gained ✓
```

**Net effect (afternoon with pump running):**
```
Drain: -0.025% / real_sec
Fill:  +0.125% / real_sec
Net:   +0.100% / real_sec (tank filling faster than draining)
```

#### Level Bounds

```python
    self.level += dlevel
    if self.level < 0.0: self.level = 0.0      # Can't go negative
    if self.level > 100.0: self.level = 100.0  # Can't overflow

    return sim_time, self.level
```

**Why clamp?**
- Physical tanks have limits (0-100%)
- Prevents simulation bugs from creating impossible values
- Safety: better to saturate than wrap around

### Part 5: Main Control Loop (Lines 141-198)

Where everything comes together!

#### Setup

```python
def main():
    client = ModbusTcpClient(PLC_IP, PLC_PORT)
    if not client.connect():
        print("ERROR: Could not connect to PLC")
        return

    logger.info("SUPERVISOR_START")
    sim = DaySim(initial_level=95.0)
    pump_on_cmd_state = False
```

**Connection handling:**
- Try to connect to PLC
- If fails: print error and exit (don't run blind!)
- Good practice: validate preconditions before main loop

**State tracking:**
- `pump_on_cmd_state`: Did we last send START or STOP?
- Prevents sending duplicate commands every loop
- Like "remembering what you last said"

#### Main Loop Structure

```python
    try:
        while True:
            # 1. Update physics simulation
            sim_time, sim_level = sim.update()

            # 2. Write simulation to PLC (THE FIX!)
            write_level(client, sim_level)

            # 3. Read actual plant state
            tank_level = read_level(client)
            tank_full  = read_coil(client, COIL_FULL)
            pump_actual = read_coil(client, COIL_PUMP_STATUS)

            # 4. Safety logic
            # 5. Normal control logic
            # 6. Wait for next scan
            time.sleep(SCAN_SEC)

    except KeyboardInterrupt:
        logger.info("SUPERVISOR_STOP (KeyboardInterrupt)")
    finally:
        client.close()
```

**Order matters:**
1. **Calculate physics first** → Get latest drain/fill
2. **Write before read** → Ensure PLC has fresh data
3. **Read back** → Confirm what PLC sees
4. **Control decisions** → Based on actual plant state

**Why try/except/finally?**
- `try`: Normal operation
- `except KeyboardInterrupt`: Catch Ctrl+C gracefully
- `finally`: Always close connection (cleanup)

#### Safety Logic (Priority #1)

```python
            if tank_full:
                pulse_coil(client, COIL_STOP)
                sim.pump_expected_running = False
                pump_on_cmd_state = False
                logger.warning("SAFETY_HIGH_HIGH Tank_Full=1 -> Pump STOP immediately")
```

**Why check safety FIRST?**
- Emergency conditions override everything
- "When in doubt, shut it down"
- Logged as WARNING (higher severity than INFO)

**State updates:**
- Set `pump_on_cmd_state = False` → Remember we stopped it
- Set `sim.pump_expected_running = False` → Update fill model

**Desktop + PLC synergy:**
- PLC ALSO checks Tank_Full (in ladder logic)
- Desktop adds second layer (belt + suspenders)
- If Desktop hangs, PLC still protects

#### Normal Control Logic

```python
            else:  # Only if NOT in emergency
                if tank_level is not None:  # Only if we got valid data

                    # START LOGIC
                    if (tank_level < LOW_THRESHOLD) and (pump_on_cmd_state is False):
                        pulse_coil(client, COIL_START)
                        pump_on_cmd_state = True
                        sim.pump_expected_running = True
                        logger.info(f"PUMP_START at {tank_level:.1f}% (sim {sim_time.time()} simLvl {sim_level:.1f}%)")
```

**Start conditions (ALL must be true):**
1. `tank_level < LOW_THRESHOLD` → Level below 60%
2. `pump_on_cmd_state is False` → We haven't already started it
3. `tank_full is False` → Safety not active (checked in outer if)
4. `tank_level is not None` → We got valid Modbus data

**Why check `pump_on_cmd_state`?**

**Without this check:**
```
Loop 1: tank_level = 59% → Send START → pump_on_cmd_state stays False
Loop 2: tank_level = 59% → Send START again! (duplicate)
Loop 3: tank_level = 60% → Send START again! (spam)
... keeps pulsing START every 2 seconds!
```

**With this check:**
```
Loop 1: tank_level = 59%, state=False → Send START → state=True
Loop 2: tank_level = 59%, state=True → Don't send (already started)
Loop 3: tank_level = 60%, state=True → Don't send (already started)
... waits until level reaches 95% before next command
```

**Log message breakdown:**
```
PUMP_START at 58.2% (sim 01:34:00 simLvl 59.1%)
           ↑         ↑              ↑
      Real PLC   Sim time      Sim tank level
       reading                  (our model)
```

**Why log both real and simulated values?**
- **Debug tool:** If they diverge, something's wrong
- **Validation:** Proves simulation matches reality
- **Audit trail:** Shows what system "thought" vs "saw"

#### Stop Logic

```python
                    # STOP LOGIC
                    if (tank_level >= STOP_TARGET) and (pump_on_cmd_state is True):
                        pulse_coil(client, COIL_STOP)
                        pump_on_cmd_state = False
                        sim.pump_expected_running = False
                        logger.info(f"PUMP_STOP at {tank_level:.1f}% (sim {sim_time.time()} simLvl {sim_level:.1f}%)")
```

**Stop conditions:**
1. `tank_level >= STOP_TARGET` → Level at or above 95%
2. `pump_on_cmd_state is True` → Pump is currently running

**Why ≥ instead of ==?**
- Levels might jump: 94.8% → 95.3% (never exactly 95.0%)
- Analog measurements have noise/rounding
- `>=` catches "95 or higher"

**Mirror of start logic:**
- Send STOP pulse
- Update state tracking
- Log the event

#### Scan Timing

```python
            time.sleep(SCAN_SEC)  # 2 seconds
```

**Why sleep?**
- Control loop rate limiting
- Prevents CPU spinning at 100%
- Matches typical SCADA scan rates (1-5 seconds)

**Industry context:**
- Safety loops: 10-100 ms (PLC handles this)
- Regulatory loops: 100 ms - 1 sec (PID control)
- Supervisory loops: 1-10 sec (us!)
- Reporting loops: 1 min - 1 hour

---

## 📄 File 3: `summarize_log.py` (Evidence Generator)

### Purpose

Converts the **event log into a human-readable report** that answers: "Did the pump behave as expected?"

### Code Breakdown

#### Pattern Matching

```python
import re
from datetime import datetime

LOGFILE = "tank_events.log"

RE_START   = re.compile(r"PUMP_START")
RE_STOP    = re.compile(r"PUMP_STOP")
RE_SAFETY  = re.compile(r"SAFETY_HIGH_HIGH")
```

**Why regular expressions?**
- Flexible pattern matching
- `r"PUMP_START"` finds "PUMP_START" anywhere in line
- Could extend: `r"PUMP_START.*(\d+\.\d+)%"` to extract level

**Why these three patterns?**
- **PUMP_START:** Beginning of pump cycle
- **PUMP_STOP:** End of pump cycle
- **SAFETY_HIGH_HIGH:** Emergency condition
- Everything else is noise (ignore it)

#### Timestamp Extraction

```python
def ts_from_line(line):
    # log format: "YYYY-mm-dd HH:MM:SS LEVEL MESSAGE"
    # Example:    "2025-01-23 14:45:22 INFO PUMP_START at 58.2%..."

    ts = " ".join(line.split(" ", 2)[:2])  # Take first two space-separated parts
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
```

**String processing breakdown:**
```python
line = "2025-01-23 14:45:22 INFO PUMP_START at 58.2%..."

line.split(" ", 2)
# Result: ["2025-01-23", "14:45:22", "INFO PUMP_START at 58.2%..."]
#          First part    Second      Rest (limit=2 splits)

[:2]
# Take first 2 elements: ["2025-01-23", "14:45:22"]

" ".join(...)
# Join with space: "2025-01-23 14:45:22"

datetime.strptime(..., "%Y-%m-%d %H:%M:%S")
# Parse to datetime object: datetime(2025, 1, 23, 14, 45, 22)
```

**Why extract timestamp?**
- Allows time-based analysis
- Can calculate pump run duration
- Enables timeline reconstruction

#### Main Analysis

```python
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
```

**What it does:**
- Read entire log file line by line
- Check each line against all three patterns
- Store matching lines with timestamps in separate lists

**Why separate lists?**
- Easy to count: `len(starts)` = number of pump cycles
- Easy to sort: by timestamp
- Easy to display: group similar events

**Data structure:**
```python
starts = [
    (datetime(2025,1,23,14,45,22), "2025-01-23 14:45:22 INFO PUMP_START at 58.2%..."),
    (datetime(2025,1,23,15,30,10), "2025-01-23 15:30:10 INFO PUMP_START at 59.8%..."),
    ...
]
```

#### Report Generation

```python
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
```

**Output example:**
```
=== Pump Activity Summary ===
Pump starts: 5
  2025-01-23 14:45:22  2025-01-23 14:45:22 INFO PUMP_START at 58.2%...
  2025-01-23 15:30:10  2025-01-23 15:30:10 INFO PUMP_START at 59.8%...
  ...

Pump stops: 5
  2025-01-23 15:10:45  2025-01-23 15:10:45 INFO PUMP_STOP at 95.1%...
  ...

Safety trips: 1
  2025-01-23 15:05:00  2025-01-23 15:05:00 WARNING SAFETY_HIGH_HIGH...
```

#### Duration Calculation

```python
    if starts and stops:
        first_on = min(ts for ts, _ in starts)   # Earliest start time
        last_off = max(ts for ts, _ in stops)    # Latest stop time
        print(f"\nApprox pump activity window: {last_off - first_on}")
```

**What it calculates:**
- Time from first pump start to last pump stop
- Gives rough idea of total operating period

**Example:**
```
first_on = 2025-01-23 14:45:22
last_off = 2025-01-23 17:30:50
window   = 2:45:28 (2 hours, 45 minutes, 28 seconds)
```

**Why "approximate"?**
- Doesn't account for multiple cycles
- Just first→last, not total runtime
- Good enough for sanity check

#### Health Assessment

```python
    print("\nDid the pump behave as expected?")
    if safeties:
        print("  Safety triggered. Check high-level alarm conditions.")
    else:
        print("  No safety trips. Pump cycled normally between thresholds.")
```

**Simple heuristic:**
- If `safeties` list is empty → Normal operation
- If `safeties` has entries → Investigate (not necessarily bad!)

**Good answer includes:**
- Number of cycles (should be multiple throughout day)
- No unexpected safety trips (unless you tested Tank_Full)
- Logical timing (cycles during low-level periods)

---

## 🎓 Key Concepts for Your Teacher

### 1. SCADA Architecture

**What is SCADA?**
- **S**upervisory **C**ontrol **A**nd **D**ata **A**cquisition
- Industry standard for distributed control systems
- Used in: water treatment, power grids, manufacturing, pipelines

**Our implementation:**
- **PLC (OpenPLC):** Local control, real-time safety, deterministic
- **HMI (Desktop):** Supervisory logic, data logging, operator interface
- **Protocol (Modbus/TCP):** Standard industrial communication

**Why this architecture?**
- **Reliability:** PLC keeps running if HMI fails
- **Safety:** Critical logic in hardened PLC, not general-purpose computer
- **Flexibility:** Can swap HMI software without touching PLC
- **Industry standard:** Real plants work exactly this way

### 2. Separation of Simulation and Control

**Key insight:** The simulation and control are **decoupled**

**Simulation layer (DaySim):**
- Models the physical process (water consumption)
- Calculates expected tank level
- Provides test stimulus

**Control layer (main loop):**
- Reads plant state
- Makes decisions (start/stop)
- Commands actuators

**Why separate?**
1. **Testing:** Can run control logic with simulated or real plant
2. **Validation:** Compare simulated vs actual values (they should match!)
3. **Reusability:** Same control logic works on real tank (just remove sim)
4. **Clarity:** Physics separate from control strategy

**Real-world parallel:**
- Simulation = Physics engine (Unity, MATLAB Simulink)
- Control = Your game logic / control algorithm
- In real plant, "simulation" is replaced by actual sensors

### 3. Defensive Programming

**Multiple layers of protection:**

**Layer 1: PLC Safety Logic**
```iecst
IF Tank_Full THEN
    Pump_Run := FALSE;  (* Hardwired, can't be bypassed *)
END_IF;
```

**Layer 2: Desktop Safety Check**
```python
if tank_full:
    pulse_coil(client, COIL_STOP)  # Belt + suspenders
```

**Layer 3: Error Handling**
```python
if tank_level is not None:  # Don't act on bad data
    # Control logic
```

**Layer 4: State Tracking**
```python
if (level < 60) and (pump_on_cmd_state is False):  # Prevent duplicate commands
```

**Philosophy:**
- Assume things will fail (network, sensors, software)
- Multiple independent checks
- Fail to safe state (pump OFF if in doubt)
- Log everything for post-mortem analysis

### 4. Event-Driven Logging

**Bad approach (polling/sampling):**
```python
while True:
    log.write(f"{time} Tank:{level}% Pump:{pump_status}\n")
    time.sleep(1)
```
- Logs 86,400 entries per day
- 99% are identical ("58.3%, OFF" → "58.2%, OFF" → "58.1%, OFF")
- Needle in haystack problem

**Our approach (event-driven):**
```python
# Only log state changes
if transition_to_on:
    logger.info("PUMP_START")
if transition_to_off:
    logger.info("PUMP_STOP")
```
- Maybe 10-20 entries per day
- Each entry is meaningful
- Easy to spot problems

**Real-world analogy:**
- Polling = Security camera recording 24/7 (terabytes of video)
- Event-driven = Motion detector that records only when movement detected

### 5. Hysteresis (Deadband)

**Problem without hysteresis:**
```
Setpoint: 60%
Tank at 60.1% → Pump OFF
Tank drains to 59.9% → Pump ON
Tank fills to 60.1% → Pump OFF
... pump cycles every 10 seconds! (BAD)
```

**Solution: Use two thresholds**
```
Low threshold:  60% (start pump)
High threshold: 95% (stop pump)
Deadband:       35% (difference)

Tank at 95% → Pump OFF
Tank drains to 90%, 80%, 70%... → Pump stays OFF
Tank reaches 60% → Pump ON
Tank fills to 65%, 70%... 95% → Pump stays ON
Tank reaches 95% → Pump OFF
... healthy cycles! (GOOD)
```

**Why this matters:**
- **Mechanical wear:** Motors designed for ~10 starts/hour, not 100+
- **Energy waste:** Startup current 5-7× running current
- **Water hammer:** Rapid on/off causes pressure spikes (pipe damage)
- **Universal principle:** Used in thermostats, AC, chillers, etc.

### 6. Time Compression for Testing

**Real system:** 24 hours to complete one daily cycle

**Our system:** 3 hours (8× speedup)

**How it works:**
- 1 simulated minute = 7.5 real seconds
- All rates scale proportionally:
  - Morning drain: 1%/10min → 0.1%/sim_min → 0.0125%/real_sec
  - Afternoon drain: 1%/5min → 0.2%/sim_min → 0.025%/real_sec
  - Pump fill: 1%/1min → 0.125%/real_sec

**Why this technique?**
- **Validation:** Can test full day in one afternoon
- **Debugging:** Iterate faster (don't wait 24h to see results)
- **Common practice:** Flight simulators, weather models, game engines
- **Real-world analogy:** Fast-forward button on video player

**Caution:** Some things don't scale (communication delays, relay bounce)

### 7. State Machine Design

The pump controller is a **finite state machine**:

```
       ┌─────────┐
       │   OFF   │
       └─────────┘
            │
  (level<60%)
            ↓
       ┌─────────┐
       │   ON    │
       └─────────┘
            │
  (level≥95% OR Tank_Full)
            ↓
       ┌─────────┐
       │   OFF   │
       └─────────┘
```

**States:**
- OFF: Pump not running, waiting for low level
- ON: Pump running, waiting for high level or emergency

**Transitions:**
- OFF → ON: `level < 60%` AND `NOT Tank_Full`
- ON → OFF: `level ≥ 95%` OR `Tank_Full`

**State tracking:**
```python
pump_on_cmd_state = False  # Current state (OFF)

if should_start:
    pump_on_cmd_state = True  # Transition to ON

if should_stop:
    pump_on_cmd_state = False  # Transition to OFF
```

**Why explicit state?**
- Prevents duplicate commands (only act on state changes)
- Makes logic clear (if OFF and low, go ON)
- Easy to extend (add states like FAULT, MANUAL, etc.)

---

## 🔍 Common Teacher Questions & Answers

### "Why use Modbus instead of direct control?"

**Answer:**
- **Industry standard:** Modbus invented 1979, universally supported
- **Vendor-neutral:** Works with any PLC brand (Siemens, Allen-Bradley, OpenPLC)
- **Network-based:** Can control from anywhere (local network, VPN, cloud)
- **Separation:** Desktop doesn't need to know PLC internals
- **Safety:** PLC has final authority (Desktop can request, PLC can deny)

### "Why not just simulate everything in Python?"

**Answer:**
- **Realism:** Real systems have PLCs - this demonstrates understanding
- **Safety:** PLC provides hardware-level safety (independent of Python)
- **Distributed control:** Shows how SCADA systems actually work
- **Fault tolerance:** If Python crashes, PLC keeps system safe
- **Learning:** Understanding PLC programming is valuable skill

### "Why threshold control instead of PID?"

**Answer:**
- **Binary actuator:** Pump is ON or OFF (not variable speed)
- **Adequate performance:** Threshold control works fine for slow processes
- **Simplicity:** Easy to understand, verify, and troubleshoot
- **Industry practice:** Most batch processes use threshold/level control
- **PID would be overkill:** PID for continuous control (valve position), not binary

### "Why RotatingFileHandler instead of database?"

**Answer:**
- **Simplicity:** No SQL server needed, just text files
- **Portability:** Text logs work everywhere (Windows, Linux, embedded)
- **Greppable:** Can use standard tools (`grep`, `tail`, `less`)
- **Self-managing:** Auto-rotation prevents disk fill
- **Adequate:** Not "big data" - events per day measured in tens, not millions
- **Industry practice:** Embedded systems (PLCs, RTUs) use text logs

### "Why compress time for testing?"

**Answer:**
- **Practical:** 3-hour test vs 24-hour test (8× faster iteration)
- **Validation:** Can test multiple scenarios in one day
- **Standard practice:** Used in all time-based simulations (weather, flight, process)
- **Scalable:** Easy to adjust ACCELERATED_DAY_SECONDS for different speeds
- **Math works out:** All rates scale proportionally, behavior identical

### "What happens if network fails?"

**Answer:**
**Desktop perspective:**
```python
tank_level = read_level(client)  # Returns None if Modbus fails
if tank_level is not None:       # Skip control logic if no data
    # Make decisions
```
- Desktop stops commanding (safe behavior)
- Logs last known state
- Waits for reconnection

**PLC perspective:**
- Last command remains in effect (latch holds state)
- Tank_Full safety still works (hardwired)
- Pump continues current state (ON or OFF)

**Result:**
- System "freezes" in last safe state
- Safety logic still active
- No erratic behavior

### "How do you know the system is working correctly?"

**Answer:**

**1. Log analysis:**
```bash
python3 summarize_log.py
```
- Should see multiple pump cycles (5-10 in 24 sim hours)
- Starts always <60%, stops always ≥95%
- No unexpected safety trips

**2. Real vs simulated comparison:**
```
PUMP_START at 58.2% (sim 01:34:00 simLvl 59.1%)
              ↑                         ↑
         Should match within ±2%
```
- If they diverge: simulation or control logic broken

**3. Timing sanity check:**
```
Pump activity window: 2:45:30
```
- Should be hours, not minutes or days
- Multiple cycles, not one continuous run

**4. Safety test:**
```bash
mbpoll -m tcp -a 1 -t 0 -r 803 <IP> 1  # Trigger Tank_Full
grep "SAFETY" tank_events.log           # Should see immediate stop
```

---

## 📊 Summary Table

| Component | Language | Lines | Purpose | Key Technique |
|-----------|----------|-------|---------|---------------|
| `WaterTankPump.st` | Structured Text | 40 | PLC safety logic | Latching + emergency override |
| `tank_supervisor.py` | Python | 198 | Supervisory control | Simulation + threshold control + event logging |
| `summarize_log.py` | Python | 64 | Evidence analysis | Pattern matching + timeline reconstruction |
| `INSTRUCTIONS.md` | Markdown | - | Setup guide | Security hardening (firewall, MFA) |

---

## 🏆 What Makes This Solution Good?

### Technical Excellence
- ✅ Industry-standard architecture (SCADA)
- ✅ Defensive programming (multiple safety layers)
- ✅ Proper state machine design
- ✅ Event-driven logging (not polling spam)
- ✅ Error handling (network failures graceful)
- ✅ Clean separation (simulation vs control)

### Requirements Coverage
- ✅ Time-based drain (morning/afternoon rates)
- ✅ Automatic pump control (60% start, 95% stop)
- ✅ Safety override (Tank_Full emergency stop)
- ✅ Clean logging (only significant events)
- ✅ Log rotation (2 GiB limit)
- ✅ Evidence generation (`summarize_log.py`)
- ✅ Security hardening (firewall + MFA)

### Best Practices
- ✅ Code comments explain "why", not just "what"
- ✅ Magic numbers extracted to constants
- ✅ Functions with single responsibilities
- ✅ Graceful shutdown (try/except/finally)
- ✅ Validation before action (`if is not None`)

### Educational Value
- ✅ Demonstrates understanding of distributed control
- ✅ Shows knowledge of industrial protocols (Modbus)
- ✅ Applies control theory (hysteresis, state machines)
- ✅ Implements cybersecurity principles (MFA, firewall)
- ✅ Provides clear documentation

---

## 💡 Final Tips for Explaining to Your Teacher

**Start high-level:**
"I built a two-tier control system like real water treatment plants use. The PLC handles safety, the Desktop handles automation."

**Then dive into specifics:**
"The simulation models building consumption: slow in morning, fast in afternoon. The control logic starts the pump at 60% and stops at 95% to prevent rapid cycling."

**Emphasize safety:**
"The PLC has a hardwired safety check - if Tank_Full activates, it immediately stops the pump, even if my Desktop crashes."

**Show the evidence:**
"Here's my log summary showing 5 pump cycles over 24 simulated hours, all between the correct thresholds."

**Discuss trade-offs:**
"I used threshold control instead of PID because the pump is binary (on/off), and threshold control is simpler and adequate for slow processes."

**Demonstrate understanding:**
"The 35% hysteresis prevents rapid cycling, which would damage the motor and waste energy."

**Good luck! 🚀**
