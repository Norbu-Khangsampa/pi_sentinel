"""Colour-blob detection used by the sentinel control loop."""

import cv2
import numpy as np


def build_mask(frame, lower, upper):
    """Return a cleaned-up binary mask of pixels inside the HSV range."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
    # remove speckle noise, then restore the size of real blobs
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)
    return mask


def find_target(frame, lower, upper, min_area=300):
    """Find the largest blob in the HSV range.

    Returns (cx, cy, area) in pixel coordinates, or None if nothing big
    enough is in view.
    """
    mask = build_mask(frame, lower, upper)
    # [-2] keeps this working on both OpenCV 3 and OpenCV 4
    contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    if area < min_area:
        return None

    m = cv2.moments(largest)
    if m["m00"] == 0:
        return None
    return int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"]), area
