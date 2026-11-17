"""Default settings for Pi Sentinel.

Every value here can be overridden from the command line of sentinel.py,
so this file only needs editing to change the defaults permanently.
"""

# --- Camera -----------------------------------------------------------------
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# --- Servo (SG90 on GPIO 18 / physical pin 12) ------------------------------
SERVO_GPIO = 18
SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180
SERVO_CENTER_ANGLE = 90
SERVO_MIN_PULSE = 0.0005   # 500 us  -> 0 degrees
SERVO_MAX_PULSE = 0.0025   # 2500 us -> 180 degrees

# --- Target colour (HSV), found with tools/color_tuner.py --------------------
HSV_LOWER = (27, 35, 147)
HSV_UPPER = (49, 87, 203)
MIN_TARGET_AREA = 300      # ignore blobs smaller than this many pixels

# --- Control loop -----------------------------------------------------------
KP = 0.05                  # degrees of correction per pixel of error
DEADBAND_PX = 20           # don't move when the target is this close to centre
SERVO_DIRECTION = -1       # flip to +1 if the servo turns away from the target
