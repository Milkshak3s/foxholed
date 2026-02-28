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
        frame = capture.capture_screen()
        if frame is None:
            window.set_status(f"No window found matching \"{config.window_title}\"")
            window.set_confidence(None)
            window.map_widget.update_position(None)
            return

        minimap = capture.crop_minimap(frame)
        position = detector.detect(minimap)

        if position is not None:
            window.update_position(
                region_name=position.region_name,
                grid_x=position.grid_x,
                grid_y=position.grid_y,
                confidence=position.confidence,
            )
        else:
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
