"""Screen capture module - find the Foxhole game window and grab the minimap region."""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

import mss
import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from foxholed.config import Config

log = logging.getLogger(__name__)


def _find_window_geometry(title: str) -> dict | None:
    """Find a window by title and return its geometry as an mss-compatible dict.

    Uses xdotool on Linux to locate the window. Returns None if the window
    is not found or xdotool is unavailable.
    """
    try:
        result = subprocess.run(
            ["xdotool", "search", "--name", title],
            capture_output=True,
            text=True,
            timeout=2,
        )
        window_ids = result.stdout.strip().splitlines()
        if not window_ids:
            return None

        # Use the first matching window
        wid = window_ids[0]

        result = subprocess.run(
            ["xdotool", "getwindowgeometry", "--shell", wid],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode != 0:
            return None

        # Parse output like: WINDOW=123\nX=100\nY=200\nWIDTH=800\nHEIGHT=600
        geo = {}
        for line in result.stdout.strip().splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                geo[key] = val

        x, y = int(geo["X"]), int(geo["Y"])
        w, h = int(geo["WIDTH"]), int(geo["HEIGHT"])

        return {"left": x, "top": y, "width": w, "height": h}

    except FileNotFoundError:
        log.warning("xdotool not found - install it for window detection (apt install xdotool)")
        return None
    except (subprocess.TimeoutExpired, KeyError, ValueError):
        log.debug("Failed to get window geometry", exc_info=True)
        return None


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
        geo = _find_window_geometry(self.config.window_title)
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
            return None

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
