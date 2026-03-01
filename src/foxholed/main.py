"""Entry point - sets up the QApplication, detection worker, and map window."""

from __future__ import annotations

import logging
import signal
import sys
import threading

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from foxholed.config import Config
from foxholed.detection_worker import DetectionWorker
from foxholed.detector import Position
from foxholed.region_notifier import RegionNotifier
from foxholed.settings import load_settings, save_settings
from foxholed.ui.map_window import MapWindow
from foxholed.ui.template_dialog import TemplateCaptureDialog
from foxholed.war_api import fetch_faction_control

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
    notifier = RegionNotifier()

    # Update template count on startup
    window.set_template_count(worker.detector.template_count)

    # ------------------------------------------------------------------
    # War API polling (runs in background thread, updates UI via signal)
    # ------------------------------------------------------------------

    def _poll_war_api() -> None:
        try:
            control = fetch_faction_control()
            if control:
                # Schedule UI update on the main thread
                QTimer.singleShot(0, lambda: window.map_widget.set_faction_control(control))
                log.info("War API: updated faction control for %d regions", len(control))
        except Exception:
            log.debug("War API poll failed", exc_info=True)

    def _start_api_poll() -> None:
        threading.Thread(target=_poll_war_api, daemon=True).start()

    # Poll every 60 seconds
    api_timer = QTimer()
    api_timer.timeout.connect(_start_api_poll)
    api_timer.start(60_000)
    # Initial poll
    _start_api_poll()

    # ------------------------------------------------------------------
    # Detection signals
    # ------------------------------------------------------------------

    def on_position(position: Position | None) -> None:
        if position is not None:
            window.update_position(
                region_name=position.region_name,
                grid_x=position.grid_x,
                grid_y=position.grid_y,
                confidence=position.confidence,
                method=position.method,
            )
            notifier.update(position.region_name)
        else:
            window.set_confidence(None)
            window.map_widget.update_position(None)

    def on_status(text: str) -> None:
        window.set_status(text)

    def on_capture_status(status: str) -> None:
        window.set_capture_status(status)

    def on_capture_template_requested() -> None:
        worker.request_frame_capture()

    def on_frame_captured(frame) -> None:
        # Try to find the triangle and crop around it
        marker = worker.detector.find_player_triangle(frame)
        if marker is None:
            window.set_status("Open the map (M) before capturing")
            return

        crop, _ = worker.detector._crop_around(frame, *marker)
        dialog = TemplateCaptureDialog(crop, config.templates_dir, parent=window)
        if dialog.exec():
            worker.detector.reload_templates()
            window.set_template_count(worker.detector.template_count)
            window.region_view.clear_cache()

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
