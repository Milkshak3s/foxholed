"""Dialog for capturing and saving minimap templates."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from foxholed.map_data import REGIONS


class TemplateCaptureDialog(QDialog):
    """Dialog to preview a minimap capture and save it as a template."""

    def __init__(
        self,
        frame: np.ndarray,
        templates_dir: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Capture Template")
        self._frame = frame
        self._templates_dir = templates_dir

        layout = QVBoxLayout(self)

        # Minimap preview
        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_preview(frame)
        layout.addWidget(self._preview)

        # Region name dropdown
        region_layout = QHBoxLayout()
        region_layout.addWidget(QLabel("Region:"))
        self._region_combo = QComboBox()
        region_names = sorted(r.name for r in REGIONS)
        self._region_combo.addItems(region_names)
        region_layout.addWidget(self._region_combo, stretch=1)
        layout.addLayout(region_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _set_preview(self, frame: np.ndarray) -> None:
        """Display the frame in the preview label."""
        if len(frame.shape) == 2:
            h, w = frame.shape
            qimg = QImage(frame.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self._preview.setPixmap(scaled)

    def _on_save(self) -> None:
        """Save the minimap as a grayscale template."""
        region_name = self._region_combo.currentText()
        if not region_name:
            return

        self._templates_dir.mkdir(parents=True, exist_ok=True)
        save_path = self._templates_dir / f"{region_name}.png"

        if len(self._frame.shape) == 3:
            gray = cv2.cvtColor(self._frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = self._frame

        cv2.imwrite(str(save_path), gray)
        self.accept()
