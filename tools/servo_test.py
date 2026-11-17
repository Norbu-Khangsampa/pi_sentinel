"""Sweep the SG90 servo through centre, left and right to check wiring and range."""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config  # noqa: E402
from servo import Servo  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--gpio", type=int, default=config.SERVO_GPIO)
parser.add_argument("--software-pwm", action="store_true",
                    help="skip hardware PWM and use gpiozero/lgpio software PWM")
args = parser.parse_args()

servo = Servo(
    gpio=args.gpio,
    min_angle=config.SERVO_MIN_ANGLE,
    max_angle=config.SERVO_MAX_ANGLE,
    min_pulse=config.SERVO_MIN_PULSE,
    max_pulse=config.SERVO_MAX_PULSE,
    prefer_hardware=not args.software_pwm,
)
print(f"SG90 servo on GPIO {args.gpio} using {servo.backend} PWM")
if servo.backend == "software" and not args.software_pwm:
    print(f"  (hardware PWM unavailable: {getattr(servo, 'fallback_reason', 'unknown')})")

try:
    for label, angle, pause in [
        ("centre", 90, 1.5),
        ("left", 0, 1.5),
        ("right", 180, 1.5),
        ("centre", 90, 1.0),
    ]:
        print(f"Moving to {angle} degrees ({label})")
        servo.angle = angle
        time.sleep(pause)
except KeyboardInterrupt:
    pass
finally:
    # stop the pulse train so the servo doesn't buzz or jitter at rest
    servo.detach()
    servo.close()
    print("Test complete.")
