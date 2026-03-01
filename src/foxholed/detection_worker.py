"""Background QThread for screen capture and position detection."""

from __future__ import annotations

import logging
import time

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from foxholed.capture import ScreenCapture
from foxholed.config import Config
from foxholed.detector import Position, PositionDetector

log = logging.getLogger(__name__)


class DetectionWorker(QThread):
    """Runs capture -> crop -> detect in a background thread."""

    position_detected = pyqtSignal(object)  # Position | None
    status_changed = pyqtSignal(str)
    capture_status_changed = pyqtSignal(str)  # "ok" | "no_window" | "no_match"
    frame_captured = pyqtSignal(object)  # np.ndarray (minimap)

    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._capture = ScreenCapture(config)
        self._detector = PositionDetector(config)
        self._interval_ms = config.capture_interval_ms
        self._running = False
        self._frame_requested = False

    @property
    def detector(self) -> PositionDetector:
        return self._detector

    def set_interval(self, ms: int) -> None:
        """Change the capture interval (thread-safe)."""
        self._interval_ms = ms

    def request_frame_capture(self) -> None:
        """Request a frame to be emitted via frame_captured on next tick."""
        self._frame_requested = True

    def stop(self) -> None:
        """Signal the worker to stop and wait for it to finish."""
        self._running = False
        self.wait()

    def run(self) -> None:
        self._running = True
        log.info("Detection worker started")

        while self._running:
            try:
                self._tick()
            except Exception:
                log.exception("Detection tick failed")
                self.status_changed.emit("Detection error")

            # Sleep in 100ms increments for responsive shutdown
            elapsed = 0
            while self._running and elapsed < self._interval_ms:
                time.sleep(min(0.1, (self._interval_ms - elapsed) / 1000))
                elapsed += 100

        log.info("Detection worker stopped")

    def _tick(self) -> None:
        frame = self._capture.capture_screen()
        if frame is None:
            self.status_changed.emit(
                f'No window found matching "{self._config.window_title}"'
            )
            self.capture_status_changed.emit("no_window")
            self.position_detected.emit(None)
            return

        minimap = self._capture.crop_minimap(frame)

        # If a frame was requested for template capture, emit it
        if self._frame_requested:
            self._frame_requested = False
            self.frame_captured.emit(minimap.copy())

        position = self._detector.detect(minimap)
        self.position_detected.emit(position)

        if position is None:
            self.capture_status_changed.emit("no_match")
            if self._detector.template_count == 0:
                self.status_changed.emit(
                    "No templates loaded. Use 'Capture Template' to create one."
                )
            else:
                self.status_changed.emit("Position: detecting...")
        else:
            self.capture_status_changed.emit("ok")
