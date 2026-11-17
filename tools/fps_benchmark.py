"""Measure how many frames per second the camera pipeline delivers.

Runs headless by default; pass --show to also display the frames.
"""

import argparse
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config  # noqa: E402
from vision import VideoStream  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--seconds", type=float, default=10.0)
parser.add_argument("--show", action="store_true")
parser.add_argument("--usb-camera", metavar="SRC", default=None)
args = parser.parse_args()

if args.show and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    print("[WARN] No display found, running headless")
    args.show = False

resolution = (config.FRAME_WIDTH, config.FRAME_HEIGHT)
if args.usb_camera is not None:
    src = int(args.usb_camera) if args.usb_camera.isdigit() else args.usb_camera
    vs = VideoStream(src=src, resolution=resolution, use_picamera=False).start()
else:
    vs = VideoStream(resolution=resolution).start()

print(f"[INFO] Camera backend: {vs.backend}")
print(f"[INFO] Running performance test for {args.seconds:g} seconds...")

frames = 0
start = time.monotonic()
try:
    while time.monotonic() - start < args.seconds:
        frame = vs.next_frame(timeout=2.0)
        if frame is None:
            print("[WARN] No frame received in 2 s")
            continue
        frames += 1
        if args.show:
            cv2.imshow("Pi Sentinel - FPS Test", frame)
            cv2.waitKey(1)
except KeyboardInterrupt:
    pass

elapsed = time.monotonic() - start
vs.stop()
if args.show:
    cv2.destroyAllWindows()

print("--- PERFORMANCE RESULTS ---")
print(f"Total frames: {frames}")
print(f"Elapsed time: {elapsed:.2f} seconds")
print(f"Average FPS:  {frames / elapsed:.2f}")
