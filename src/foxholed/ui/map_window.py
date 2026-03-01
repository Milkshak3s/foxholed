"""Main application window containing the map widget and status bar."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QToolBar,
    QWidget,
)

from foxholed.config import Config
from foxholed.ui.map_widget import MapWidget
from foxholed.ui.overlay_widget import OverlayWidget
from foxholed.ui.region_view_widget import RegionViewWidget
from foxholed.window_utils import list_windows


class MapWindow(QMainWindow):
    """Top-level window for the Foxholed map viewer."""

    capture_interval_changed = pyqtSignal(int)
    capture_template_requested = pyqtSignal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("Foxholed - Map Position Reader")
        self.resize(900, 700)

        # Central map widget
        self.map_widget = MapWidget(hex_size=config.hex_size, parent=self)
        self.setCentralWidget(self.map_widget)

        # Settings toolbar
        toolbar = QToolBar("Settings", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addWidget(QLabel(" Window: "))
        self._title_combo = QComboBox()
        self._title_combo.setEditable(True)
        self._title_combo.setMaximumWidth(300)
        self._title_combo.setMinimumWidth(200)
        self._populate_windows()
        self._title_combo.currentTextChanged.connect(self._on_title_changed)
        toolbar.addWidget(self._title_combo)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._populate_windows)
        toolbar.addWidget(self._refresh_btn)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Interval (ms): "))
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(100, 10000)
        self._interval_spin.setSingleStep(100)
        self._interval_spin.setValue(config.capture_interval_ms)
        self._interval_spin.valueChanged.connect(self.capture_interval_changed)
        toolbar.addWidget(self._interval_spin)

        toolbar.addSeparator()

        self._capture_btn = QPushButton("Capture Template")
        self._capture_btn.clicked.connect(self.capture_template_requested)
        toolbar.addWidget(self._capture_btn)

        toolbar.addSeparator()

        # Always-on-top toggle
        self._aot_checkbox = QCheckBox("Always on Top")
        self._aot_checkbox.toggled.connect(self._on_always_on_top_toggled)
        toolbar.addWidget(self._aot_checkbox)

        toolbar.addSeparator()

        # Center-on-player button
        self._center_btn = QPushButton("Center on Player")
        self._center_btn.clicked.connect(self._center_on_player)
        toolbar.addWidget(self._center_btn)

        toolbar.addSeparator()

        # Compact overlay toggle
        self._overlay_checkbox = QCheckBox("Overlay")
        self._overlay_checkbox.toggled.connect(self._on_overlay_toggled)
        toolbar.addWidget(self._overlay_checkbox)

        toolbar.addSeparator()

        # Region view toggle
        self._region_view_checkbox = QCheckBox("Region View")
        self._region_view_checkbox.setChecked(True)
        self._region_view_checkbox.toggled.connect(self._on_region_view_toggled)
        toolbar.addWidget(self._region_view_checkbox)

        # Status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)

        # Status indicator dot
        self._status_dot = QLabel()
        self._set_status_dot("red")

        self._position_label = QLabel("Position: unknown")
        self._last_update_label = QLabel("")
        self._template_count_label = QLabel("Templates: 0")
        self._confidence_label = QLabel("Confidence: -")

        self._status_bar.addWidget(self._status_dot)
        self._status_bar.addWidget(self._position_label, stretch=1)
        self._status_bar.addPermanentWidget(self._last_update_label)
        self._status_bar.addPermanentWidget(self._template_count_label)
        self._status_bar.addPermanentWidget(self._confidence_label)

        self._last_detection_time: float | None = None

        # Timer to refresh the "last detected" display
        self._staleness_timer = QTimer(self)
        self._staleness_timer.timeout.connect(self._update_staleness)
        self._staleness_timer.start(1000)

        # Keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Home), self, self._center_on_player)
        QShortcut(QKeySequence(Qt.Key.Key_0), self, self.map_widget.reset_view)
        QShortcut(QKeySequence(Qt.Key.Key_Plus), self, self.map_widget.zoom_in)
        QShortcut(QKeySequence(Qt.Key.Key_Equal), self, self.map_widget.zoom_in)
        QShortcut(QKeySequence(Qt.Key.Key_Minus), self, self.map_widget.zoom_out)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.map_widget.pan_left)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.map_widget.pan_right)
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, self.map_widget.pan_up)
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, self.map_widget.pan_down)

        # Overlay widget (lazy-created)
        self._overlay: OverlayWidget | None = None

        # Region view dock (right panel)
        self.region_view = RegionViewWidget(config.templates_dir, parent=self)
        self._region_dock = QDockWidget("Region View", self)
        self._region_dock.setWidget(self.region_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._region_dock)
        self._region_dock.visibilityChanged.connect(
            lambda vis: self._region_view_checkbox.setChecked(vis)
        )

        self.set_status("Waiting for game...")

    # ------------------------------------------------------------------
    # Always-on-top
    # ------------------------------------------------------------------

    def _on_always_on_top_toggled(self, checked: bool) -> None:
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()  # re-show required after changing window flags

    def set_always_on_top(self, checked: bool) -> None:
        """Set the always-on-top state (e.g. from saved settings)."""
        self._aot_checkbox.setChecked(checked)

    def is_always_on_top(self) -> bool:
        return self._aot_checkbox.isChecked()

    # ------------------------------------------------------------------
    # Center on player
    # ------------------------------------------------------------------

    def _center_on_player(self) -> None:
        self.map_widget.center_on_player()

    # ------------------------------------------------------------------
    # Compact overlay
    # ------------------------------------------------------------------

    def _on_overlay_toggled(self, checked: bool) -> None:
        if checked:
            if self._overlay is None:
                self._overlay = OverlayWidget()
            self._overlay.show()
        else:
            if self._overlay is not None:
                self._overlay.hide()

    # ------------------------------------------------------------------
    # Region view dock
    # ------------------------------------------------------------------

    def _on_region_view_toggled(self, checked: bool) -> None:
        self._region_dock.setVisible(checked)

    # ------------------------------------------------------------------
    # Status indicator dot
    # ------------------------------------------------------------------

    def _set_status_dot(self, color: str) -> None:
        self._status_dot.setFixedSize(14, 14)
        self._status_dot.setStyleSheet(
            f"background-color: {color}; border-radius: 7px; margin: 2px;"
        )

    def set_capture_status(self, status: str) -> None:
        """Update the status dot: 'ok' (green), 'no_window' (red), 'no_match' (yellow)."""
        colors = {"ok": "#4CAF50", "no_window": "#F44336", "no_match": "#FFC107"}
        self._set_status_dot(colors.get(status, "#F44336"))

    # ------------------------------------------------------------------
    # Staleness / last update
    # ------------------------------------------------------------------

    def _update_staleness(self) -> None:
        if self._last_detection_time is None:
            self._last_update_label.setText("")
            return
        elapsed = time.time() - self._last_detection_time
        if elapsed < 60:
            self._last_update_label.setText(f"Last: {elapsed:.0f}s ago")
        else:
            mins = int(elapsed // 60)
            self._last_update_label.setText(f"Last: {mins}m ago")

    # ------------------------------------------------------------------
    # Window list
    # ------------------------------------------------------------------

    def _populate_windows(self) -> None:
        """Refresh the window combo box with currently open windows."""
        current = self._title_combo.currentText() or self.config.window_title
        self._title_combo.blockSignals(True)
        self._title_combo.clear()
        titles = list_windows()
        self._title_combo.addItems(titles)
        idx = self._title_combo.findText(current)
        if idx >= 0:
            self._title_combo.setCurrentIndex(idx)
        else:
            self._title_combo.setEditText(current)
        self._title_combo.blockSignals(False)

    def _on_title_changed(self, text: str) -> None:
        self.config.window_title = text

    # ------------------------------------------------------------------
    # Status bar updates
    # ------------------------------------------------------------------

    def set_status(self, text: str) -> None:
        """Update the position text in the status bar."""
        self._position_label.setText(text)

    def set_confidence(self, value: float | None) -> None:
        """Update the confidence display."""
        if value is None:
            self._confidence_label.setText("Confidence: -")
        else:
            self._confidence_label.setText(f"Confidence: {value:.0%}")

    def set_template_count(self, count: int) -> None:
        """Update the template count display in the status bar."""
        self._template_count_label.setText(f"Templates: {count}")
        if count == 0:
            self._template_count_label.setStyleSheet("color: red;")
        else:
            self._template_count_label.setStyleSheet("")

    def update_position(
        self,
        region_name: str | None,
        grid_x: float | None = None,
        grid_y: float | None = None,
        confidence: float | None = None,
        method: str | None = None,
    ) -> None:
        """Update both the map marker and the status bar."""
        self.map_widget.update_position(region_name, grid_x, grid_y)
        if self._overlay is not None and self._overlay.isVisible():
            self._overlay.update_position(region_name, grid_x, grid_y)
        self.region_view.update_position(region_name, grid_x or 0.0, grid_y or 0.0)

        if region_name is None:
            self.set_status("Position: unknown")
            self.set_capture_status("no_match")
        else:
            self._last_detection_time = time.time()
            self.set_capture_status("ok")
            method_label = (method or "template").upper()
            parts = [f"{method_label}: {region_name}"]
            if grid_x is not None and grid_y is not None:
                parts.append(f"Grid: ({grid_x:.2f}, {grid_y:.2f})")
            self.set_status(" | ".join(parts))

        self.set_confidence(confidence)

    # ------------------------------------------------------------------
    # Window geometry save/restore helpers
    # ------------------------------------------------------------------

    def get_geometry_dict(self) -> dict:
        geo = self.geometry()
        return {"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height()}

    def restore_geometry_dict(self, d: dict) -> None:
        if all(k in d for k in ("x", "y", "width", "height")):
            self.setGeometry(d["x"], d["y"], d["width"], d["height"])
