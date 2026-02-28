"""Main application window containing the map widget and status bar."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
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
from foxholed.window_utils import list_windows


class MapWindow(QMainWindow):
    """Top-level window for the Foxholed map viewer."""

    capture_interval_changed = pyqtSignal(int)

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

        # Status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)

        self._position_label = QLabel("Position: unknown")
        self._confidence_label = QLabel("Confidence: -")
        self._status_bar.addWidget(self._position_label, stretch=1)
        self._status_bar.addPermanentWidget(self._confidence_label)

        self.set_status("Waiting for game...")

    def _populate_windows(self) -> None:
        """Refresh the window combo box with currently open windows."""
        current = self._title_combo.currentText() or self.config.window_title
        self._title_combo.blockSignals(True)
        self._title_combo.clear()
        titles = list_windows()
        self._title_combo.addItems(titles)
        # Restore / pre-select the configured title
        idx = self._title_combo.findText(current)
        if idx >= 0:
            self._title_combo.setCurrentIndex(idx)
        else:
            self._title_combo.setEditText(current)
        self._title_combo.blockSignals(False)

    def _on_title_changed(self, text: str) -> None:
        self.config.window_title = text

    def set_status(self, text: str) -> None:
        """Update the position text in the status bar."""
        self._position_label.setText(text)

    def set_confidence(self, value: float | None) -> None:
        """Update the confidence display."""
        if value is None:
            self._confidence_label.setText("Confidence: -")
        else:
            self._confidence_label.setText(f"Confidence: {value:.0%}")

    def update_position(
        self,
        region_name: str | None,
        grid_x: float | None = None,
        grid_y: float | None = None,
        confidence: float | None = None,
    ) -> None:
        """Update both the map marker and the status bar."""
        self.map_widget.update_position(region_name, grid_x, grid_y)

        if region_name is None:
            self.set_status("Position: unknown")
        else:
            parts = [f"Region: {region_name}"]
            if grid_x is not None and grid_y is not None:
                parts.append(f"Grid: ({grid_x:.2f}, {grid_y:.2f})")
            self.set_status(" | ".join(parts))

        self.set_confidence(confidence)
