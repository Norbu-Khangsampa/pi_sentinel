"""Pi Sentinel: pan a camera-mounted SG90 servo to keep a coloured target centred.

Runs headless by default (no windows, status goes to the log), so it can be
started over SSH or as a systemd service. Pass --show to open a preview
window when a desktop session is available.
"""

import argparse
import logging
import os
import signal
import sys
import time

import cv2

import config
from servo import Servo
from tracker import find_target
from vision import VideoStream

log = logging.getLogger("sentinel")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--show", action="store_true",
                   help="open a preview window (needs a desktop or VNC session)")
    p.add_argument("--usb-camera", metavar="SRC", default=None,
                   help="use a V4L2/USB camera (e.g. 0 or /dev/video0) instead of the CSI Arducam")
    p.add_argument("--width", type=int, default=config.FRAME_WIDTH)
    p.add_argument("--height", type=int, default=config.FRAME_HEIGHT)
    p.add_argument("--gpio", type=int, default=config.SERVO_GPIO)
    p.add_argument("--kp", type=float, default=config.KP,
                   help="proportional gain in degrees per pixel (default: %(default)s)")
    p.add_argument("--deadband", type=int, default=config.DEADBAND_PX)
    p.add_argument("--invert", action="store_true",
                   help="reverse the servo direction if it turns away from the target")
    p.add_argument("--software-pwm", action="store_true",
                   help="skip hardware PWM and use gpiozero/lgpio software PWM")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def display_available():
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _raise_interrupt(signum, frame):
    raise KeyboardInterrupt


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    show = args.show
    if show and not display_available():
        log.warning("--show ignored: no display found (running headless)")
        show = False

    # Let systemd's SIGTERM go through the same clean-shutdown path as Ctrl+C
    signal.signal(signal.SIGTERM, _raise_interrupt)

    if args.usb_camera is not None:
        src = int(args.usb_camera) if args.usb_camera.isdigit() else args.usb_camera
        stream = VideoStream(src=src, resolution=(args.width, args.height), use_picamera=False)
    else:
        stream = VideoStream(resolution=(args.width, args.height))
    stream.start()
    log.info("Camera started (%s, %dx%d)", stream.backend, args.width, args.height)

    if stream.next_frame(timeout=5.0) is None:
        log.error("No frames from the camera after 5 s, giving up")
        stream.stop()
        return 1

    servo = Servo(
        gpio=args.gpio,
        min_angle=config.SERVO_MIN_ANGLE,
        max_angle=config.SERVO_MAX_ANGLE,
        min_pulse=config.SERVO_MIN_PULSE,
        max_pulse=config.SERVO_MAX_PULSE,
        prefer_hardware=not args.software_pwm,
    )
    if servo.backend == "software" and not args.software_pwm:
        log.warning("Hardware PWM unavailable (%s); using software PWM",
                    getattr(servo, "fallback_reason", "unknown"))
    log.info("Servo on GPIO %d using %s PWM", args.gpio, servo.backend)

    angle = config.SERVO_CENTER_ANGLE
    servo.angle = angle
    time.sleep(0.5)

    direction = -config.SERVO_DIRECTION if args.invert else config.SERVO_DIRECTION
    center_x = args.width / 2
    frames = 0
    last_report = time.monotonic()
    target = None

    try:
        while True:
            frame = stream.next_frame(timeout=1.0)
            if frame is None:
                log.warning("Camera stalled, waiting for frames...")
                continue
            frames += 1

            target = find_target(frame, config.HSV_LOWER, config.HSV_UPPER,
                                 config.MIN_TARGET_AREA)
            if target is not None:
                cx, cy, _ = target
                error = cx - center_x
                if abs(error) > args.deadband:
                    angle += direction * args.kp * error
                    angle = max(config.SERVO_MIN_ANGLE, min(config.SERVO_MAX_ANGLE, angle))
                    servo.angle = angle

            now = time.monotonic()
            if now - last_report >= 2.0:
                fps = frames / (now - last_report)
                if target is not None:
                    log.info("%.1f fps | target x=%d y=%d | servo %.1f deg",
                             fps, target[0], target[1], angle)
                else:
                    log.info("%.1f fps | no target | servo %.1f deg", fps, angle)
                frames = 0
                last_report = now

            if show:
                if target is not None:
                    cv2.circle(frame, (target[0], target[1]), 50, (0, 255, 255), 2)
                cv2.line(frame, (int(center_x), 0), (int(center_x), args.height), (255, 0, 0), 1)
                cv2.imshow("Pi Sentinel", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Shutting down")
        servo.angle = config.SERVO_CENTER_ANGLE
        time.sleep(0.3)
        servo.detach()
        servo.close()
        stream.stop()
        if show:
            cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
