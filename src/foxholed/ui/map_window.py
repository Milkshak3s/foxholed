"""Main application window containing the map widget and status bar."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMainWindow, QStatusBar, QWidget

from foxholed.config import Config
from foxholed.ui.map_widget import MapWidget


class MapWindow(QMainWindow):
    """Top-level window for the Foxholed map viewer."""

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("Foxholed - Map Position Reader")
        self.resize(900, 700)

        # Central map widget
        self.map_widget = MapWidget(hex_size=config.hex_size, parent=self)
        self.setCentralWidget(self.map_widget)

        # Status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)

        self._position_label = QLabel("Position: unknown")
        self._confidence_label = QLabel("Confidence: -")
        self._status_bar.addWidget(self._position_label, stretch=1)
        self._status_bar.addPermanentWidget(self._confidence_label)

        self.set_status("Waiting for game...")

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
