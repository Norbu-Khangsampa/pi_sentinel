"""Threaded camera capture for the Raspberry Pi 5.

The Pi 5 drives CSI cameras (such as the Arducam modules) through libcamera,
so cv2.VideoCapture(0) cannot open them. This class uses Picamera2 when a CSI
camera is detected and falls back to a V4L2 device (USB webcam) otherwise.
Frames are always returned as BGR numpy arrays, ready for OpenCV.
"""

import sys
import threading

import cv2

try:
    from picamera2 import Picamera2
except ImportError:  # not installed, or not running on a Pi
    Picamera2 = None


def csi_camera_available():
    if Picamera2 is None:
        return False
    try:
        return len(Picamera2.global_camera_info()) > 0
    except Exception:
        return False


class VideoStream:
    def __init__(self, src=0, resolution=(640, 480), use_picamera=None):
        """
        src          -- V4L2 device index or path, used only for USB cameras
        resolution   -- (width, height) of the captured frames
        use_picamera -- True/False to force a backend, None to auto-detect
        """
        if use_picamera is None:
            use_picamera = csi_camera_available()
        self.use_picamera = use_picamera
        self.resolution = resolution

        self.frame = None
        self.frame_id = 0
        self.stopped = False
        self._last_served_id = 0
        self._cond = threading.Condition()
        self._thread = None

        if self.use_picamera:
            self.camera = Picamera2()
            # "RGB888" in libcamera terms is stored B, G, R in memory,
            # which is exactly the channel order OpenCV expects.
            config = self.camera.create_video_configuration(
                main={"size": resolution, "format": "RGB888"}
            )
            self.camera.configure(config)
            self.camera.start()
        else:
            if sys.platform.startswith("linux"):
                self.camera = cv2.VideoCapture(src, cv2.CAP_V4L2)
            else:
                self.camera = cv2.VideoCapture(src)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
            if not self.camera.isOpened():
                raise RuntimeError(
                    f"Could not open camera {src!r}. Check the ribbon cable or "
                    "USB connection and run 'rpicam-hello --list-cameras'."
                )

    @property
    def backend(self):
        return "picamera2" if self.use_picamera else "v4l2"

    def start(self):
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _grab(self):
        if self.use_picamera:
            return self.camera.capture_array("main")
        ok, frame = self.camera.read()
        return frame if ok else None

    def _update(self):
        while not self.stopped:
            frame = self._grab()
            if frame is None:
                continue
            with self._cond:
                self.frame = frame
                self.frame_id += 1
                self._cond.notify_all()

    def read(self):
        """Return the most recent frame (may be None before the first one arrives)."""
        with self._cond:
            return self.frame

    def next_frame(self, timeout=1.0):
        """Block until a frame newer than the last one returned here is ready.

        Returns None on timeout. Using this instead of read() stops a control
        loop from reacting to the same frame more than once.
        """
        with self._cond:
            ready = self._cond.wait_for(
                lambda: self.frame_id > self._last_served_id or self.stopped,
                timeout,
            )
            if not ready or self.stopped:
                return None
            self._last_served_id = self.frame_id
            return self.frame

    def stop(self):
        self.stopped = True
        with self._cond:
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self.use_picamera:
            self.camera.stop()
            self.camera.close()
        else:
            self.camera.release()
