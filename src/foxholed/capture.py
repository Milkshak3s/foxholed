"""Screen capture module - find the Foxhole game window and grab the minimap region."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import mss
import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from foxholed.config import Config

log = logging.getLogger(__name__)


class ScreenCapture:
    """Captures screenshots from the Foxhole game window."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._sct = mss.mss()

    def find_game_monitor(self) -> dict | None:
        """Find a monitor/screen to capture.

        mss doesn't do window-title matching directly, so we capture the
        primary monitor. A future enhancement could use platform APIs to
        locate the actual Foxhole window bounds.

        Returns:
            Monitor dict for mss, or None if no monitors available.
        """
        monitors = self._sct.monitors
        if len(monitors) < 2:
            return None
        # monitors[0] is the virtual screen combining all, monitors[1] is primary
        return monitors[1]

    def capture_screen(self) -> np.ndarray | None:
        """Capture the primary monitor as a numpy BGR array.

        Returns:
            numpy array (H, W, 3) in BGR format, or None on failure.
        """
        monitor = self.find_game_monitor()
        if monitor is None:
            return None

        try:
            shot = self._sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            return np.array(img)[:, :, ::-1]  # RGB -> BGR for OpenCV
        except Exception:
            log.exception("Screen capture failed")
            return None

    def crop_minimap(self, frame: np.ndarray) -> np.ndarray:
        """Crop the minimap region from a full screen capture.

        Args:
            frame: Full screen image as numpy BGR array.

        Returns:
            Cropped minimap region.
        """
        r = self.config.minimap_region
        return frame[r.y : r.y + r.height, r.x : r.x + r.width]
