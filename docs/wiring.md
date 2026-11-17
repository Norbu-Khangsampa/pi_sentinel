# Pi Sentinel – Wiring

## Parts

| Part | Notes |
|------|-------|
| Raspberry Pi 5 | Raspberry Pi OS Bookworm (64-bit), Lite works fine |
| Arducam CSI camera | Connected to CAM/DISP 0 with the Pi 5 (22-pin) ribbon cable |
| SG90 micro servo | 4.8–6 V, ~500–2500 µs pulse range |
| 5 V supply for the servo | Recommended: a separate 5 V supply or a BEC |

## SG90 servo → Raspberry Pi 5

| SG90 wire | Connects to | Pi header pin |
|-----------|-------------|---------------|
| Orange (signal) | GPIO 18 (PWM0 ch 2) | Pin 12 |
| Red (+5 V) | 5 V | Pin 2 or 4 (or external 5 V) |
| Brown (GND) | GND | Pin 6 |

```
 Pi 5 header (top-left corner)
   3V3  (1) (2)  5V   <-- servo red
  GPIO2 (3) (4)  5V
  GPIO3 (5) (6)  GND  <-- servo brown
  GPIO4 (7) (8)  GPIO14
    GND (9) (10) GPIO15
 GPIO17 (11)(12) GPIO18 <-- servo orange (signal)
```

**Power note:** a servo stalling or starting up can draw several hundred mA,
which can brown out the Pi. If you power the servo from an external 5 V
supply, **connect its ground to a Pi GND pin** so the signal has a common
reference. A 470–1000 µF capacitor across the servo's 5 V and GND smooths
the current spikes.

## Camera

1. Power the Pi off and lift the connector latch on **CAM/DISP 0**.
2. Insert the ribbon cable with the contacts facing the connector's
   contacts, then press the latch closed.
3. Most Arducam modules are detected automatically. If yours isn't, add the
   overlay Arducam lists for your sensor to `/boot/firmware/config.txt`,
   for example:
   ```
   camera_auto_detect=0
   dtoverlay=imx519,cam0
   ```
4. Check it with `rpicam-hello --list-cameras`.

## Enabling hardware PWM on GPIO 18

Add this line to `/boot/firmware/config.txt` and reboot:

```
dtoverlay=pwm-2chan,pin=18,func=2,pin2=19,func2=2
```

Check it after the reboot:

```bash
pinctrl get 18          # should report a PWM0 function, not "input"/"none"
ls /sys/class/pwm/      # a pwmchip should be present
```

Without the overlay, `servo.py` falls back to software PWM automatically
(the log will say so). Software PWM works but the servo may twitch slightly.
