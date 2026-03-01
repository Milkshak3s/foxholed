"""Entry point - sets up the QApplication, detection worker, and map window."""

from __future__ import annotations

import logging
import signal
import sys

from PyQt6.QtWidgets import QApplication

from foxholed.config import Config
from foxholed.detection_worker import DetectionWorker
from foxholed.detector import Position
from foxholed.settings import load_settings, save_settings
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

    # Load persisted settings
    saved = load_settings(config)

    window = MapWindow(config)

    # Restore window geometry
    if "window_geometry" in saved:
        window.restore_geometry_dict(saved["window_geometry"])
    # Restore map view state
    if "map_view" in saved:
        window.map_widget.restore_view_state(saved["map_view"])
    # Restore always-on-top
    if saved.get("always_on_top"):
        window.set_always_on_top(True)
    # Restore interval spinner to match loaded config
    window._interval_spin.setValue(config.capture_interval_ms)

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

    def on_capture_status(status: str) -> None:
        window.set_capture_status(status)

    def on_capture_template_requested() -> None:
        worker.request_frame_capture()

    def on_frame_captured(minimap) -> None:
        dialog = TemplateCaptureDialog(minimap, config.templates_dir, parent=window)
        if dialog.exec():
            worker.detector.reload_templates()
            window.set_template_count(worker.detector.template_count)

    def on_shutdown() -> None:
        save_settings(
            config,
            window_geometry=window.get_geometry_dict(),
            map_view=window.map_widget.get_view_state(),
            always_on_top=window.is_always_on_top(),
        )
        worker.stop()

    worker.position_detected.connect(on_position)
    worker.status_changed.connect(on_status)
    worker.capture_status_changed.connect(on_capture_status)
    worker.frame_captured.connect(on_frame_captured)
    window.capture_interval_changed.connect(worker.set_interval)
    window.capture_template_requested.connect(on_capture_template_requested)

    app.aboutToQuit.connect(on_shutdown)
    worker.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
