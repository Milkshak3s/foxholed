"""Persistent user settings backed by a JSON file.

Settings are stored at the platform-appropriate config directory
(e.g. ~/.config/foxholed/settings.json on Linux).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from platformdirs import user_config_dir

from foxholed.config import Config, MinimapRegion

log = logging.getLogger(__name__)

SETTINGS_DIR = Path(user_config_dir("foxholed", appauthor=False))
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


def load_settings(config: Config) -> dict:
    """Load saved settings into config, returning the raw dict for UI state."""
    if not SETTINGS_FILE.exists():
        return {}

    try:
        data = json.loads(SETTINGS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        log.warning("Failed to read settings file, using defaults")
        return {}

    if "window_title" in data:
        config.window_title = data["window_title"]
    if "capture_interval_ms" in data:
        config.capture_interval_ms = data["capture_interval_ms"]
    if "match_confidence_threshold" in data:
        config.match_confidence_threshold = data["match_confidence_threshold"]
    if "minimap_region" in data:
        mr = data["minimap_region"]
        config.minimap_region = MinimapRegion(
            x=mr.get("x", 0),
            y=mr.get("y", 0),
            width=mr.get("width", 300),
            height=mr.get("height", 300),
        )

    log.info("Loaded settings from %s", SETTINGS_FILE)
    return data


def save_settings(
    config: Config,
    *,
    window_geometry: dict | None = None,
    map_view: dict | None = None,
    always_on_top: bool = False,
) -> None:
    """Save current settings to disk."""
    data: dict = {
        "window_title": config.window_title,
        "capture_interval_ms": config.capture_interval_ms,
        "match_confidence_threshold": config.match_confidence_threshold,
        "minimap_region": {
            "x": config.minimap_region.x,
            "y": config.minimap_region.y,
            "width": config.minimap_region.width,
            "height": config.minimap_region.height,
        },
        "always_on_top": always_on_top,
    }

    if window_geometry is not None:
        data["window_geometry"] = window_geometry
    if map_view is not None:
        data["map_view"] = map_view

    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(data, indent=2))
        log.debug("Saved settings to %s", SETTINGS_FILE)
    except OSError:
        log.warning("Failed to save settings", exc_info=True)


def reset_settings() -> None:
    """Delete the settings file to restore defaults."""
    try:
        SETTINGS_FILE.unlink(missing_ok=True)
        log.info("Settings reset to defaults")
    except OSError:
        log.warning("Failed to reset settings", exc_info=True)
