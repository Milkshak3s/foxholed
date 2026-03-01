"""Notifies the user when the detected region changes."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import QApplication

log = logging.getLogger(__name__)


class RegionNotifier:
    """Tracks the current region and emits an audio cue on change."""

    def __init__(self) -> None:
        self._current_region: str | None = None

    def update(self, region_name: str | None) -> str | None:
        """Update with a new detection result.

        Returns:
            The new region name if it changed, otherwise None.
        """
        if region_name is None or region_name == self._current_region:
            return None

        old = self._current_region
        self._current_region = region_name

        if old is not None:
            log.info("Region changed: %s -> %s", old, region_name)
            app = QApplication.instance()
            if app is not None:
                app.beep()

        return region_name

    @property
    def current_region(self) -> str | None:
        return self._current_region
