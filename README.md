# Pi Sentinel

A pan-tracking camera for the Raspberry Pi 5. An Arducam CSI camera is mounted
on an SG90 servo. OpenCV finds a coloured object in each frame, and a
proportional controller pans the servo to keep the object centred.

Runs headless by default, so it can be started over SSH or as a systemd
service.

## How it works

1. `vision.py` captures frames in a background thread with Picamera2
   (falling back to a USB camera if no CSI camera is found).
2. `tracker.py` converts each frame to HSV, masks the target colour, and
   finds the centroid of the largest blob.
3. `sentinel.py` turns the horizontal offset from the frame centre into a
   servo correction: `angle += Kp × error`, with a deadband to stop jitter.
4. `servo.py` drives the SG90 with the Pi 5's hardware PWM on GPIO 18,
   falling back to software PWM when the overlay isn't enabled.

## Project structure

```
pi_sentinel/
├── src/
│   ├── sentinel.py       main tracking loop
│   ├── vision.py         threaded camera capture (Picamera2 / V4L2)
│   ├── servo.py          SG90 driver (hardware PWM with software fallback)
│   ├── tracker.py        HSV colour-blob detection
│   └── config.py         default pins, colours and gains
├── tools/
│   ├── servo_test.py     sweep the servo to check wiring
│   ├── fps_benchmark.py  measure camera throughput
│   └── color_tuner.py    interactive HSV calibration (needs a display)
├── deploy/
│   └── sentinel.service  systemd unit for starting at boot
├── docs/
│   └── wiring.md         full wiring, camera and power notes
└── requirements.txt
```

## Hardware

- Raspberry Pi 5 running Raspberry Pi OS Bookworm (64-bit, Lite or Desktop)
- Arducam CSI camera module on **CAM/DISP 0**
- SG90 micro servo
- Optional: a separate 5 V supply for the servo, with its ground tied to the Pi

| SG90 wire | Pi 5 |
|-----------|------|
| Orange (signal) | GPIO 18, pin 12 |
| Red (+5 V) | Pin 2 or 4 |
| Brown (GND) | Pin 6 |

See [`docs/wiring.md`](docs/wiring.md) for the header diagram, camera setup
and power advice.

## Quickstart

```bash
# 1. System packages (Picamera2 is only available from apt)
sudo apt update
sudo apt install -y python3-opencv python3-numpy python3-picamera2 \
                    python3-gpiozero python3-lgpio

# 2. Enable hardware PWM on GPIO 18 for smooth servo control
echo "dtoverlay=pwm-2chan,pin=18,func=2,pin2=19,func2=2" | sudo tee -a /boot/firmware/config.txt
sudo reboot

# 3. Check the hardware
rpicam-hello --list-cameras
python3 tools/servo_test.py        # servo sweeps centre → left → right → centre
python3 tools/fps_benchmark.py     # camera throughput, headless

# 4. Run the tracker
python3 src/sentinel.py            # headless, status printed to the log
python3 src/sentinel.py --show     # with a preview window (desktop/VNC only)
```

If you use a virtual environment, create it with
`python3 -m venv --system-site-packages .venv` so it can see Picamera2.

### Options

| Flag | Purpose |
|------|---------|
| `--invert` | Reverse the servo direction if it turns away from the target |
| `--kp 0.03` | Proportional gain (degrees per pixel); lower it if the servo oscillates |
| `--deadband 20` | Pixels from centre within which the servo holds still |
| `--usb-camera 0` | Use a USB webcam instead of the CSI camera |
| `--software-pwm` | Skip hardware PWM (it's used automatically when the overlay is missing) |
| `-v` | Debug logging |

## Calibrating the target colour

`tools/color_tuner.py` opens HSV sliders with live mask and result views. It
needs a screen, so run it from the Pi desktop, over VNC, or with `ssh -X`.
Press `q` when only the target shows white, then paste the printed
`HSV_LOWER` / `HSV_UPPER` values into `src/config.py`.

## Running at boot

Edit `User` and the paths in `deploy/sentinel.service` to match your Pi, then:

```bash
sudo cp deploy/sentinel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sentinel
journalctl -u sentinel -f
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `No frames from the camera` | Check the ribbon cable orientation and run `rpicam-hello --list-cameras` |
| Log says "using software PWM" | The PWM overlay isn't active; check `/boot/firmware/config.txt` and reboot |
| Servo oscillates around the target | Lower `--kp` or raise `--deadband` |
| Servo turns away from the target | Add `--invert` |
| Pi reboots when the servo moves | Power the servo from a separate 5 V supply (common ground) |
