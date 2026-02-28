"""Screen capture module - find the Foxhole game window and grab the minimap region."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import mss
import numpy as np
from PIL import Image

from foxholed.window_utils import find_window_geometry

if TYPE_CHECKING:
    from foxholed.config import Config

log = logging.getLogger(__name__)


class ScreenCapture:
    """Captures screenshots from the Foxhole game window."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._sct = mss.mss()
        self._window_geo: dict | None = None

    def find_game_window(self) -> dict | None:
        """Find the Foxhole game window by its title.

        Searches for a window matching config.window_title. Caches the result
        until the next call so we re-check each tick (the window may move or
        close).

        Returns:
            mss-compatible region dict, or None if the window isn't found.
        """
        geo = find_window_geometry(self.config.window_title)
        self._window_geo = geo
        return geo

    def capture_screen(self) -> np.ndarray | None:
        """Capture the game window as a numpy BGR array.

        Falls back to the primary monitor if the window can't be found by
        title (e.g. xdotool unavailable).

        Returns:
            numpy array (H, W, 3) in BGR format, or None on failure.
        """
        region = self.find_game_window()
        if region is None:
            log.debug("Window %r not found", self.config.window_title)
            return None

        log.debug("Window geometry: %s", region)
        try:
            shot = self._sct.grab(region)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            return np.array(img)[:, :, ::-1]  # RGB -> BGR for OpenCV
        except Exception:
            log.exception("Screen capture failed")
            return None

    def crop_minimap(self, frame: np.ndarray) -> np.ndarray:
        """Crop the minimap region from a game window capture.

        Args:
            frame: Game window image as numpy BGR array.

        Returns:
            Cropped minimap region.
        """
        r = self.config.minimap_region
        return frame[r.y : r.y + r.height, r.x : r.x + r.width]
