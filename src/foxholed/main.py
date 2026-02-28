"""Entry point - sets up the QApplication, capture loop, and map window."""

from __future__ import annotations

import logging
import signal
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from foxholed.capture import ScreenCapture
from foxholed.config import Config
from foxholed.detector import PositionDetector
from foxholed.ui.map_window import MapWindow

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = Config()
    app = QApplication(sys.argv)

    # Allow Ctrl+C to close the app
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    window = MapWindow(config)
    window.show()

    capture = ScreenCapture(config)
    detector = PositionDetector(config)

    def tick() -> None:
        log.debug("Tick: capturing window %r", config.window_title)
        frame = capture.capture_screen()
        if frame is None:
            log.info("No window found matching %r", config.window_title)
            window.set_status(f"No window found matching \"{config.window_title}\"")
            window.set_confidence(None)
            window.map_widget.update_position(None)
            return

        log.info("Captured frame %dx%d from %r", frame.shape[1], frame.shape[0], config.window_title)
        minimap = capture.crop_minimap(frame)
        log.info("Cropped minimap region %dx%d", minimap.shape[1], minimap.shape[0])

        position = detector.detect(minimap)

        if position is not None:
            log.info(
                "Detected position: region=%s grid=(%.2f, %.2f) confidence=%.1f%%",
                position.region_name,
                position.grid_x,
                position.grid_y,
                position.confidence * 100,
            )
            window.update_position(
                region_name=position.region_name,
                grid_x=position.grid_x,
                grid_y=position.grid_y,
                confidence=position.confidence,
            )
        else:
            log.info("No position detected this tick")
            window.set_status("Position: detecting...")
            window.set_confidence(None)
            window.map_widget.update_position(None)

    timer = QTimer()
    timer.timeout.connect(tick)
    timer.start(config.capture_interval_ms)

    window.capture_interval_changed.connect(timer.setInterval)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
