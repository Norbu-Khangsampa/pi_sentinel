"""SG90 servo driver for the Raspberry Pi 5.

pigpio does not support the Pi 5, so this module drives the servo in one of
two ways:

1. Hardware PWM (preferred). The RP1 chip has a PWM block on GPIO 18
   (PWM0 channel 2). Once the overlay is enabled in /boot/firmware/config.txt
   it is exposed through sysfs and produces a jitter-free 50 Hz signal:

       dtoverlay=pwm-2chan,pin=18,func=2,pin2=19,func2=2

2. Software PWM through gpiozero + lgpio. Used automatically when the
   overlay is missing. It works, but the servo may twitch slightly.
"""

import glob
import os
import time

PERIOD_NS = 20_000_000  # 20 ms = 50 Hz, the standard hobby-servo frame

# RP1 PWM0 channel for each PWM-capable header pin on the Pi 5
RP1_PWM_CHANNELS = {12: 0, 13: 1, 18: 2, 19: 3}
RP1_PWM_DEVICE = "1f00098000.pwm"


def _find_rp1_pwmchip():
    for chip in sorted(glob.glob("/sys/class/pwm/pwmchip*")):
        try:
            with open(os.path.join(chip, "npwm")) as f:
                npwm = int(f.read())
        except (OSError, ValueError):
            continue
        if RP1_PWM_DEVICE in os.path.realpath(chip) and npwm >= 4:
            return chip
    return None


class _HardwarePWM:
    def __init__(self, gpio):
        if gpio not in RP1_PWM_CHANNELS:
            raise ValueError(f"GPIO {gpio} has no hardware PWM channel")
        chip = _find_rp1_pwmchip()
        if chip is None:
            raise RuntimeError("RP1 PWM chip not found (overlay not enabled?)")

        self.chip = chip
        self.channel = RP1_PWM_CHANNELS[gpio]
        self.path = os.path.join(chip, f"pwm{self.channel}")

        if not os.path.isdir(self.path):
            self._write(os.path.join(chip, "export"), self.channel)
            # udev needs a moment to set group permissions on the new node
            for _ in range(50):
                if os.access(os.path.join(self.path, "period"), os.W_OK):
                    break
                time.sleep(0.02)

        # duty_cycle must never exceed period, so zero it first
        self._write(os.path.join(self.path, "duty_cycle"), 0)
        self._write(os.path.join(self.path, "period"), PERIOD_NS)
        self._write(os.path.join(self.path, "enable"), 1)

    @staticmethod
    def _write(path, value):
        with open(path, "w") as f:
            f.write(str(value))

    def set_pulse(self, seconds):
        self._write(os.path.join(self.path, "duty_cycle"), int(seconds * 1e9))

    def detach(self):
        self._write(os.path.join(self.path, "duty_cycle"), 0)

    def close(self):
        try:
            self.detach()
            self._write(os.path.join(self.path, "enable"), 0)
            self._write(os.path.join(self.chip, "unexport"), self.channel)
        except OSError:
            pass


class _SoftwarePWM:
    def __init__(self, gpio, min_pulse, max_pulse):
        from gpiozero import Servo as GZServo  # lgpio backend on the Pi 5

        self._servo = GZServo(
            gpio,
            initial_value=None,
            min_pulse_width=min_pulse,
            max_pulse_width=max_pulse,
            frame_width=PERIOD_NS / 1e9,
        )
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse

    def set_pulse(self, seconds):
        span = self.max_pulse - self.min_pulse
        self._servo.value = ((seconds - self.min_pulse) / span) * 2 - 1

    def detach(self):
        self._servo.detach()

    def close(self):
        self._servo.close()


class Servo:
    def __init__(
        self,
        gpio=18,
        min_angle=0,
        max_angle=180,
        min_pulse=0.0005,
        max_pulse=0.0025,
        prefer_hardware=True,
    ):
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self._angle = None

        self._driver = None
        if prefer_hardware:
            try:
                self._driver = _HardwarePWM(gpio)
                self.backend = "hardware"
            except (OSError, RuntimeError, ValueError) as exc:
                self.fallback_reason = str(exc)
        if self._driver is None:
            self._driver = _SoftwarePWM(gpio, min_pulse, max_pulse)
            self.backend = "software"

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        value = max(self.min_angle, min(self.max_angle, float(value)))
        fraction = (value - self.min_angle) / (self.max_angle - self.min_angle)
        pulse = self.min_pulse + fraction * (self.max_pulse - self.min_pulse)
        self._driver.set_pulse(pulse)
        self._angle = value

    def detach(self):
        """Stop sending pulses so the servo relaxes and stops buzzing."""
        self._driver.detach()

    def close(self):
        self._driver.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
