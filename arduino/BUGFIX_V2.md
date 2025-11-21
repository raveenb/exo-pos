# Bug Fixes for Posture Monitor V2

## Issues Found

### Issue 1: Repeated Buzzer Triggering
**Problem**: Buzzer kept beeping every ~500ms instead of once per slouch episode.

**Root Cause**: After the buzzer pattern completed (500ms), `buzzerActive` was set to `false`. In the next loop iteration, the code saw the user was still slouching and immediately retriggered the buzzer. This created an infinite loop:
```
slouch detected → beep 500ms → stop → immediately retrigger → beep 500ms → ...
```

**Fix**: Added cooldown period between alerts:
```cpp
const unsigned long ALERT_COOLDOWN_MS = 5000;  // 5 seconds between alerts
unsigned long lastAlertTime = 0;

// Only trigger if cooldown has passed
if (now - lastAlertTime >= ALERT_COOLDOWN_MS) {
  buzzerActive = true;
  buzzerStartTime = now;
  lastAlertTime = now;
}
```

Now the system will:
1. Detect slouch for 3 seconds → beep once
2. Wait 5 seconds before allowing another beep
3. If still slouching after 5 seconds, beep again

---

### Issue 2: Always Detecting Slouch (Threshold Problem)
**Problem**: Your pitch was -12° but threshold was -75°. Since -12 > -75, the system thought you were ALWAYS slouching.

**Root Cause**: The original code used an **absolute angle threshold** (-75°), which assumed a specific sensor mounting angle. But:
- Different mounting positions give different neutral angles
- Different body types have different natural neck angles
- The calibration offset wasn't being used correctly

**Your Data**:
```json
{"pitch":-12.82, "forward_slouch":true, ...}
```
- Pitch: -12° (your actual angle)
- Threshold: -75° (old absolute value)
- Check: -12 > -75? YES → Always slouching!

**Fix**: Changed to **relative threshold** based on calibrated neutral position:
```cpp
// OLD (absolute):
const float FORWARD_SLOUCH_ANGLE = -75.0;  // Absolute angle

// NEW (relative):
const float FORWARD_SLOUCH_ANGLE = 15.0;   // 15° forward from neutral
```

Now the system:
1. Calibrates your neutral position at startup (e.g., -12°)
2. Subtracts this offset from all readings (calibrated pitch ≈ 0° when upright)
3. Checks if calibrated pitch > 15° (i.e., 15° forward from your neutral)

**Example**:
```
Neutral position: -12° (stored as pitchOffset)
Reading: -12° → Calibrated: -12 - (-12) = 0° → Good posture
Reading: +3° → Calibrated: +3 - (-12) = 15° → Slouching!
```

---

## Changes Made

### File: `posture_monitor_v2.ino`

#### 1. Changed Threshold System (lines 45-49)
```cpp
// Forward head posture (tech neck) detection
// NOTE: This is RELATIVE to your calibrated neutral position
// Positive value = head forward from neutral
const float FORWARD_SLOUCH_ANGLE = 15.0;   // Pitch threshold (degrees from neutral)
const float HYSTERESIS = 2.0;              // Deadband to prevent flickering
```

#### 2. Added Cooldown Mechanism (lines 77-81)
```cpp
unsigned long lastAlertTime = 0;  // Track last alert to prevent rapid retriggering
const unsigned long ALERT_COOLDOWN_MS = 5000;  // 5 seconds between alerts
```

#### 3. Updated Alert Logic (lines 348-356)
```cpp
// Trigger alert if held long enough AND cooldown period has passed
if (!buzzerActive && (now - slouchStartTime >= SLOUCH_HOLD_MS)) {
  // Check if enough time has passed since last alert
  if (now - lastAlertTime >= ALERT_COOLDOWN_MS) {
    buzzerActive = true;
    buzzerStartTime = now;
    lastAlertTime = now;
  }
}
```

#### 4. Improved Hysteresis (lines 364-370)
```cpp
// Only turn off buzzer if significantly better than threshold
// (pitch must go BELOW threshold minus hysteresis)
if (buzzerActive && !inBadPosture && pitch < (FORWARD_SLOUCH_ANGLE - HYSTERESIS)) {
  buzzerActive = false;
  digitalWrite(BUZZER_PIN, LOW);
}
```

#### 5. Enhanced JSON Output (lines 243-264)
Added diagnostic fields to help debug:
```cpp
Serial.print(",\"pitch\":");
Serial.print(pitch, 2);              // Calibrated angle (relative to neutral)
Serial.print(",\"pitch_raw\":");
Serial.print(pitch + pitchOffset, 2);  // Raw angle before calibration
Serial.print(",\"threshold\":");
Serial.print(FORWARD_SLOUCH_ANGLE, 1); // Show threshold for reference
```

---

## New Behavior

### Startup Sequence
1. **Initialize hardware** (100ms)
2. **Auto-calibrate** (1 second, 50 samples)
   - You should be sitting in GOOD posture during this
   - System captures your neutral neck angle
3. **Begin monitoring**

### During Use

**Good Posture**:
```json
{"timestamp":1000,"pitch":0.5,"pitch_raw":-11.8,"threshold":15.0,"forward_slouch":false,"alert_active":false}
```
- Calibrated pitch near 0° (sitting upright)
- No alert

**Slouching** (head forward >15°):
```json
{"timestamp":4000,"pitch":16.2,"pitch_raw":4.5,"threshold":15.0,"forward_slouch":true,"alert_active":false}
```
- Slouch detected, but waiting 3 seconds...

**Alert Triggered** (after 3 seconds):
```json
{"timestamp":7100,"pitch":16.8,"pitch_raw":5.1,"threshold":15.0,"forward_slouch":true,"alert_active":true}
```
- BEEP! (500ms buzzer)

**Cooldown Period** (next 5 seconds):
```json
{"timestamp":10000,"pitch":17.1,"pitch_raw":5.4,"threshold":15.0,"forward_slouch":true,"alert_active":false}
```
- Still slouching, but no beep (cooldown active)

**Second Alert** (if still slouching after 5s cooldown):
```json
{"timestamp":12200,"pitch":16.5,"pitch_raw":4.8,"threshold":15.0,"forward_slouch":true,"alert_active":true}
```
- BEEP again!

**Posture Corrected**:
```json
{"timestamp":13000,"pitch":1.2,"pitch_raw":-10.5,"threshold":15.0,"forward_slouch":false,"alert_active":false}
```
- Back to good posture, no alert

---

## Testing Instructions

### 1. Upload Fixed Code
```bash
# Open Arduino IDE
# Load: posture_monitor_v2.ino
# Upload to board
```

### 2. Calibration Test
```bash
# Open Serial Monitor (115200 baud)
# You should see:
{"status":"initialized","version":"v2","device":"posture_monitor"}
{"status":"calibrating","message":"Hold neutral position..."}
# Sit up straight during this!
{"status":"calibrated","pitch_offset":-12.34,"roll_offset":-21.56}
```

### 3. Functional Test

**Step 1**: Sit with good posture
- Watch serial output
- `pitch` should be near 0° (±5°)
- `forward_slouch` should be `false`
- No buzzer

**Step 2**: Slouch forward (lean head/neck forward)
- `pitch` should increase (go positive)
- When pitch > 15°, `forward_slouch` becomes `true`
- Wait 3 seconds...
- Buzzer should beep once (500ms)

**Step 3**: Stay slouching
- No more beeps for 5 seconds (cooldown)
- After 5 seconds, another beep

**Step 4**: Sit up straight
- `pitch` should drop below 13° (threshold - hysteresis)
- Buzzer stops
- `forward_slouch` becomes `false`

### 4. Threshold Adjustment

If the system is too sensitive or not sensitive enough:

**Too sensitive** (alerts when you feel posture is fine):
```cpp
// Increase threshold (require more forward lean)
const float FORWARD_SLOUCH_ANGLE = 20.0;  // Was 15.0
```

**Not sensitive enough** (doesn't alert when slouching):
```cpp
// Decrease threshold (more strict)
const float FORWARD_SLOUCH_ANGLE = 10.0;  // Was 15.0
```

---

## Tunable Parameters

All parameters at top of file:

```cpp
// Detection sensitivity
const float FORWARD_SLOUCH_ANGLE = 15.0;   // Degrees forward from neutral
const float SIDE_TILT_ANGLE = 15.0;        // Degrees left/right (disabled)
const float HYSTERESIS = 2.0;              // Deadband width

// Timing
const unsigned long SLOUCH_HOLD_MS = 3000;        // 3s hold before alert
const unsigned long BUZZER_DURATION_MS = 500;     // Beep length
const unsigned long ALERT_COOLDOWN_MS = 5000;     // 5s between alerts

// Features
const bool ENABLE_SIDE_TILT_ALERT = false;  // Enable lateral tilt detection

// Output
OutputMode outputMode = OUTPUT_JSON;  // or OUTPUT_SERIAL_PLOTTER
```

---

## Understanding Your Logs

### Before Fix:
```json
{"timestamp":563281,"pitch":-12.82,"roll":-21.93,"forward_slouch":true,"alert_active":false}
{"timestamp":563390,"pitch":-12.62,"roll":-21.80,"forward_slouch":true,"alert_active":true}
{"timestamp":563500,"pitch":-12.81,"roll":-21.92,"forward_slouch":true,"alert_active":true}
{"timestamp":563608,"pitch":-12.57,"roll":-21.77,"forward_slouch":true,"alert_active":true}
```

**Problems**:
1. `pitch` is -12°, but `forward_slouch` is `true` (wrong!)
2. `alert_active` flips between true/false rapidly (buzzer flickering)
3. You were probably sitting normally, but system thought you were slouching

**Why**: -12° > -75° (absolute threshold), so always detected as slouch.

### After Fix (Expected):
```json
{"timestamp":1000,"pitch":0.5,"pitch_raw":-12.1,"threshold":15.0,"forward_slouch":false,"alert_active":false}
{"timestamp":1100,"pitch":0.3,"pitch_raw":-11.9,"threshold":15.0,"forward_slouch":false,"alert_active":false}
```

**When slouching**:
```json
{"timestamp":5000,"pitch":16.2,"pitch_raw":4.5,"threshold":15.0,"forward_slouch":true,"alert_active":false}
{"timestamp":8100,"pitch":17.1,"pitch_raw":5.3,"threshold":15.0,"forward_slouch":true,"alert_active":true}
```

**Improvements**:
1. `pitch` near 0° when upright (calibrated correctly)
2. `pitch_raw` shows actual sensor angle for reference
3. `threshold` visible in output for debugging
4. `forward_slouch` only true when actually leaning forward
5. `alert_active` stays stable (no flickering)

---

## Summary of Fixes

| Issue | Before | After |
|-------|--------|-------|
| **Threshold** | Absolute -75° | Relative +15° from neutral |
| **Calibration** | Not applied correctly | Subtracts neutral offset |
| **Buzzer** | Repeats every 500ms | Once per 5 seconds |
| **Detection** | Always "slouching" | Accurate detection |
| **Output** | Basic angles | Includes raw, calibrated, threshold |

---

## Next Steps

1. **Upload and test** the fixed code
2. **Verify calibration** works (sit straight at startup)
3. **Tune threshold** if needed (adjust FORWARD_SLOUCH_ANGLE)
4. **Collect clean data** for analysis/visualization

---

**Fixed Version**: V2.1
**Date**: 2025-11-20
