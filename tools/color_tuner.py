"""Interactive HSV calibration tool for picking the target colour.

This tool needs a screen: run it from the Pi desktop, over VNC, or via
'ssh -X'. Move the sliders until only the target is white in the mask,
then press 'q' and copy the printed values into src/config.py.
"""

import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config  # noqa: E402
from vision import VideoStream  # noqa: E402

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    sys.exit("No display found. Run this from the Pi desktop, over VNC, or with 'ssh -X'.")

WINDOW = "Controls"


def nothing(_):
    # trackbars need a callback; the values are polled in the loop instead
    pass


cv2.namedWindow(WINDOW)
cv2.resizeWindow(WINDOW, 640, 240)

lo, hi = config.HSV_LOWER, config.HSV_UPPER
cv2.createTrackbar("H Min", WINDOW, lo[0], 179, nothing)
cv2.createTrackbar("H Max", WINDOW, hi[0], 179, nothing)
cv2.createTrackbar("S Min", WINDOW, lo[1], 255, nothing)
cv2.createTrackbar("S Max", WINDOW, hi[1], 255, nothing)
cv2.createTrackbar("V Min", WINDOW, lo[2], 255, nothing)
cv2.createTrackbar("V Max", WINDOW, hi[2], 255, nothing)

vs = VideoStream(resolution=(config.FRAME_WIDTH, config.FRAME_HEIGHT)).start()
print("[INFO] HSV calibration tool is live. Press 'q' to quit.")

lower = upper = None
try:
    while True:
        frame = vs.next_frame(timeout=2.0)
        if frame is None:
            continue

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([cv2.getTrackbarPos(n, WINDOW) for n in ("H Min", "S Min", "V Min")])
        upper = np.array([cv2.getTrackbarPos(n, WINDOW) for n in ("H Max", "S Max", "V Max")])

        # white = pixel in range, black = out of range
        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(frame, frame, mask=mask)

        cv2.imshow("Original Feed", frame)
        cv2.imshow("Mask", mask)
        cv2.imshow("Result", result)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
except KeyboardInterrupt:
    pass
finally:
    print("[INFO] Closing stream...")
    vs.stop()
    cv2.destroyAllWindows()

if lower is not None:
    print("\nPaste these into src/config.py:")
    print(f"HSV_LOWER = ({lower[0]}, {lower[1]}, {lower[2]})")
    print(f"HSV_UPPER = ({upper[0]}, {upper[1]}, {upper[2]})")
