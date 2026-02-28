"""Cross-platform window enumeration and geometry lookup.

Uses ctypes on Windows and xdotool on Linux.
"""

from __future__ import annotations

import logging
import subprocess
import sys

log = logging.getLogger(__name__)


def list_windows() -> list[str]:
    """Return titles of all visible, titled windows."""
    if sys.platform == "win32":
        return _list_windows_win32()
    return _list_windows_linux()


def find_window_geometry(title: str) -> dict | None:
    """Find a window by title and return its geometry as an mss-compatible dict.

    Returns ``{"left": x, "top": y, "width": w, "height": h}`` or *None*.
    """
    if sys.platform == "win32":
        return _find_window_geometry_win32(title)
    return _find_window_geometry_linux(title)


# ---------------------------------------------------------------------------
# Windows implementations
# ---------------------------------------------------------------------------


def _list_windows_win32() -> list[str]:
    import ctypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    titles: list[str] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))  # type: ignore[attr-defined]
    def enum_cb(hwnd, _lparam):  # noqa: ANN001, ANN202
        if user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if buf.value:
                titles.append(buf.value)
        return True

    user32.EnumWindows(enum_cb, 0)
    return titles


def _find_window_geometry_win32(title: str) -> dict | None:
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        return None

    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None

    return {
        "left": rect.left,
        "top": rect.top,
        "width": rect.right - rect.left,
        "height": rect.bottom - rect.top,
    }


# ---------------------------------------------------------------------------
# Linux implementations
# ---------------------------------------------------------------------------


def _list_windows_linux() -> list[str]:
    try:
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", ""],
            capture_output=True,
            text=True,
            timeout=5,
        )
        wids = result.stdout.strip().splitlines()
        titles: list[str] = []
        for wid in wids:
            name_result = subprocess.run(
                ["xdotool", "getwindowname", wid],
                capture_output=True,
                text=True,
                timeout=2,
            )
            name = name_result.stdout.strip()
            if name:
                titles.append(name)
        return titles
    except FileNotFoundError:
        log.warning("xdotool not found - install it for window enumeration")
        return []
    except subprocess.TimeoutExpired:
        log.debug("xdotool timed out while listing windows")
        return []


def _find_window_geometry_linux(title: str) -> dict | None:
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

        wid = window_ids[0]

        result = subprocess.run(
            ["xdotool", "getwindowgeometry", "--shell", wid],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode != 0:
            return None

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
