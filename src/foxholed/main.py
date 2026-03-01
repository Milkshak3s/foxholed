"""Entry point - sets up the QApplication, detection worker, and map window."""

from __future__ import annotations

import logging
import signal
import sys

from PyQt6.QtWidgets import QApplication

from foxholed.config import Config
from foxholed.detection_worker import DetectionWorker
from foxholed.detector import Position
from foxholed.ui.map_window import MapWindow
from foxholed.ui.template_dialog import TemplateCaptureDialog

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

    worker = DetectionWorker(config)

    # Update template count on startup
    window.set_template_count(worker.detector.template_count)

    def on_position(position: Position | None) -> None:
        if position is not None:
            window.update_position(
                region_name=position.region_name,
                grid_x=position.grid_x,
                grid_y=position.grid_y,
                confidence=position.confidence,
                method=position.method,
            )
        else:
            window.set_confidence(None)
            window.map_widget.update_position(None)

    def on_status(text: str) -> None:
        window.set_status(text)

    def on_capture_template_requested() -> None:
        worker.request_frame_capture()

    def on_frame_captured(minimap) -> None:
        dialog = TemplateCaptureDialog(minimap, config.templates_dir, parent=window)
        if dialog.exec():
            worker.detector.reload_templates()
            window.set_template_count(worker.detector.template_count)

    worker.position_detected.connect(on_position)
    worker.status_changed.connect(on_status)
    worker.frame_captured.connect(on_frame_captured)
    window.capture_interval_changed.connect(worker.set_interval)
    window.capture_template_requested.connect(on_capture_template_requested)

    app.aboutToQuit.connect(worker.stop)
    worker.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
