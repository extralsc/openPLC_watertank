# 🔧 Setup & Evidence Package Instructions
## Water Tank Supervisor — SCS600 ht 2025

This guide walks you through:
1. Setting up firewall protection
2. Configuring SSH multi-factor authentication (MFA)
3. Running the system and capturing evidence
4. Creating your submission package

---

## 🛡️ Part 1: Firewall Setup (Desktop/HMI)

### Install and Configure UFW (Ubuntu/Debian)

```bash
# Install UFW
sudo apt-get update
sudo apt-get install ufw

# Set default policies (deny incoming, allow outgoing)
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (port 22) - CRITICAL: Do this BEFORE enabling!
sudo ufw allow 22/tcp

# Allow Modbus/TCP communication to PLC (outbound only)
sudo ufw allow out to 193.10.236.xx port 502 proto tcp

# Optional: Restrict SSH to specific IPs only
# Example: Only allow SSH from 192.168.1.100
# sudo ufw allow from 192.168.1.100 to any port 22

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### Verify Firewall is Working

```bash
# Should show: Status: active
sudo ufw status verbose

# Test from another machine (should be blocked unless whitelisted)
ssh yourusername@desktop_ip
```

**📸 SCREENSHOT THIS for your evidence package:**
```bash
sudo ufw status verbose
```

---

## 🔐 Part 2: SSH Multi-Factor Authentication Setup

### Step 1: Install Google Authenticator

```bash
# Install the PAM module
sudo apt-get install libpam-google-authenticator
```

### Step 2: Configure Authenticator for Your User

```bash
# Run the setup wizard
google-authenticator
```

**Answer the prompts as follows:**

| Prompt | Answer | Reason |
|--------|--------|--------|
| "Do you want tokens to be time-based (y/n)?" | **y** | Standard TOTP codes |
| "Do you want me to update your ~/.google_authenticator file?" | **y** | Save configuration |
| "Do you want to disallow multiple uses of the same token?" | **y** | Prevent replay attacks |
| "Increase time skew window?" | **y** | Allow slight clock differences |
| "Enable rate-limiting?" | **y** | Prevent brute-force |

**IMPORTANT:**
- **Scan the QR code** with your phone (Google Authenticator, Authy, Microsoft Authenticator, etc.)
- **Save the emergency scratch codes** in a secure location!
- **Keep this terminal open** until you verify MFA works

### Step 3: Configure PAM for SSH

```bash
# Edit PAM SSH configuration
sudo nano /etc/pam.d/sshd
```

**Add this line at the END of the file:**
```
auth required pam_google_authenticator.so
```

Save and exit (Ctrl+X, Y, Enter)

### Step 4: Configure SSH Daemon

```bash
# Edit SSH daemon config
sudo nano /etc/ssh/sshd_config
```

**Find and modify these lines:**
```
ChallengeResponseAuthentication yes
UsePAM yes
```

If they don't exist, add them. If they say "no", change to "yes".

Save and exit (Ctrl+X, Y, Enter)

### Step 5: Restart SSH Service

```bash
sudo systemctl restart sshd
```

### Step 6: Test MFA Login (CRITICAL - Test Before Logging Out!)

**Open a NEW terminal** (keep your current session open as backup):

```bash
ssh yourusername@localhost
```

You should see:
```
Password: [enter your password]
Verification code: [enter 6-digit code from authenticator app]
```

**📸 SCREENSHOT THIS prompt for your evidence package!**

**If it doesn't work:**
- Use your backup terminal to fix the configuration
- Check `/var/log/auth.log` for errors: `sudo tail -50 /var/log/auth.log`

---

## 🚀 Part 3: Running the System

### Before You Start

1. **Set your PLC IP** in `tank_supervisor.py` (line 27):
   ```python
   PLC_IP = "193.10.236.xx"  # Replace with actual IP
   ```

2. **Verify OpenPLC is running:**
   ```bash
   mbpoll -m tcp -a 1 -t 0 -r 1 193.10.236.xx
   # Should return: [1]: 0 or 1
   ```

### Run the Full Simulation

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

### Monitor Progress (Optional)

In another terminal:
```bash
# Watch the log in real-time
tail -f tank_events.log
```

Expected log entries:
```
2025-01-23 14:30:15 INFO SUPERVISOR_START
2025-01-23 14:45:22 INFO PUMP_START at 58.2% (sim 01:34:00 simLvl 59.1%)
2025-01-23 15:10:45 INFO PUMP_STOP at 95.1% (sim 03:12:00 simLvl 95.3%)
```

---

## 🧪 Part 4: Testing Safety Features

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

**📸 SCREENSHOT THIS log entry!**

**Clear the condition:**
```bash
# Reset Tank_Full sensor (coil 803 = 0)
mbpoll -m tcp -a 1 -t 0 -r 803 193.10.236.xx 0
```

The pump should restart automatically when the level drops below 60% again.

---

## 📊 Part 5: Generate Evidence

### After Simulation Completes (or Ctrl+C)

```bash
# Run the log analyzer
python3 summarize_log.py
```

**Expected output:**
```
=== Pump Activity Summary ===
Pump starts: 5
  2025-01-23 14:45:22  INFO PUMP_START at 58.2% (sim 01:34:00 simLvl 59.1%)
  2025-01-23 15:30:10  INFO PUMP_START at 59.8% (sim 03:15:22 simLvl 60.0%)
  ...

Pump stops: 5
  2025-01-23 15:10:45  INFO PUMP_STOP at 95.1% (sim 03:12:00 simLvl 95.3%)
  ...

Safety trips: 1
  2025-01-23 15:05:00  WARNING SAFETY_HIGH_HIGH Tank_Full=1 -> Pump STOP immediately

Approx pump activity window: 2:45:30

Did the pump behave as expected?
  Safety triggered. Check high-level alarm conditions.
```

**📸 SCREENSHOT THIS summary!**

---

## 📦 Part 6: Creating Your Evidence Package

### Required Screenshots

Capture the following and save with descriptive names:

1. **Log system in action:**
   ```bash
   tail -20 tank_events.log
   ```
   Save as: `01_log_system.png`

2. **Pump start/stop events:**
   ```bash
   grep "PUMP_" tank_events.log
   ```
   Save as: `02_pump_cycles.png`

3. **Safety trigger working:**
   ```bash
   grep "SAFETY" tank_events.log
   ```
   Save as: `03_safety_trigger.png`

4. **Log summary:**
   ```bash
   python3 summarize_log.py
   ```
   Save as: `04_summary_report.png`

5. **SSH MFA login prompt:**
   ```bash
   ssh yourusername@localhost
   # Screenshot showing "Verification code:" prompt
   ```
   Save as: `05_ssh_mfa.png`

6. **Firewall status:**
   ```bash
   sudo ufw status verbose
   ```
   Save as: `06_firewall_status.png`

### Required Files

Include these in your submission:
- `tank_supervisor.py` (your control script)
- `summarize_log.py` (log analyzer)
- `WaterTankPump.st` (PLC program)
- `tank_events.log` (or excerpt showing key events)

### Write Your Description (½ page)

Create a file called `DESCRIPTION.txt` or `DESCRIPTION.md` with:

**Section 1: What You Built**
- Brief description of the supervisory control system
- Mention time-based drain simulation (morning/afternoon rates)
- Auto pump control with thresholds (60% start, 95% stop)
- Emergency safety override (Tank_Full sensor)

**Section 2: How It Behaves**
- Supervisor connects to PLC via Modbus/TCP
- Writes simulated drain to PLC based on time of day
- Monitors tank level and controls pump automatically
- Logs only significant events (starts, stops, safety trips)
- Log rotation keeps files under 2 GiB

**Section 3: Security Measures**
- UFW firewall blocks unauthorized incoming connections
- SSH requires password + TOTP code (MFA)
- Only whitelisted IPs can connect (if configured)

**Section 4: Results**
- State whether pump behaved as expected
- Reference your summarize_log.py output
- Mention number of pump cycles during simulation
- Confirm safety trigger worked correctly

---

## ✅ Self-Check: Can You Answer These?

Before submitting, verify you can clearly answer:

1. **"Did the pump behave as expected?"**
   - Check `summarize_log.py` output
   - Pump should start <60%, stop ≥95%
   - Multiple cycles throughout the day

2. **"Is the logging system working correctly?"**
   - Only significant events (no spam)
   - File size stays under 2 GiB
   - Easy to read and summarize

3. **"Is the Desktop secure?"**
   - Firewall blocks unauthorized access
   - SSH requires MFA (password + code)
   - Can demonstrate both in screenshots

4. **"Does the safety system work?"**
   - Tank_Full immediately stops pump
   - Logged as SAFETY_HIGH_HIGH
   - Pump can restart after condition clears

---

## 🔍 Troubleshooting

### Firewall Issues

**Problem:** Can't connect to PLC after enabling firewall
```bash
# Add explicit allow rule for Modbus
sudo ufw allow out to 193.10.236.xx port 502 proto tcp
sudo ufw reload
```

**Problem:** Locked out after enabling firewall
- Connect via console or VNC
- Run: `sudo ufw disable` to temporarily disable
- Fix rules, then `sudo ufw enable`

### SSH MFA Issues

**Problem:** Locked out, can't SSH
- Use console/VNC access
- Check PAM config: `cat /etc/pam.d/sshd`
- Remove the google-authenticator line temporarily
- Restart sshd: `sudo systemctl restart sshd`

**Problem:** "Verification code:" never appears
- Check SSH config: `sudo grep -i challenge /etc/ssh/sshd_config`
- Should be: `ChallengeResponseAuthentication yes`
- Restart sshd after changes

**Problem:** Code from app doesn't work
- Check phone clock is accurate
- Use emergency scratch code instead
- Verify you're using the right account's code

### Pump Control Issues

**Problem:** Pump never starts
```bash
# Check PLC connection
mbpoll -m tcp -a 1 -t 0 -r 1 193.10.236.xx

# Check tank level is being written
mbpoll -m tcp -a 1 -t 4 -r 0 193.10.236.xx
# Should show decreasing values as tank drains
```

**Problem:** Pump runs continuously
- Check stop threshold logic in code
- Verify Tank_Level register is updating
- Check PLC program is running

### Log Issues

**Problem:** Log file empty or missing events
- Check file permissions: `ls -la tank_events.log`
- Verify logger level is INFO: `logger.setLevel(logging.INFO)`
- Check for Python errors in terminal output

---

## 🏆 Success Criteria

Your submission is complete when you have:

- ✅ All 6 required screenshots
- ✅ All Python and PLC source files
- ✅ Half-page description document
- ✅ Evidence showing:
  - Log system captures key events only
  - Pump cycles automatically between thresholds
  - Safety trigger stops pump immediately
  - SSH requires MFA (password + code)
  - Firewall blocks unauthorized access
- ✅ Clear answer to: "Did the pump behave as expected?"

**Good luck! 🚀**
