"""Widget that displays a zoomed-in region template with a player position marker."""

from __future__ import annotations

import math
import time
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget


class RegionViewWidget(QWidget):
    """Displays the current region's template image with a green player dot."""

    def __init__(self, templates_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._templates_dir = templates_dir
        self._pixmap_cache: dict[str, QPixmap] = {}

        self._current_region: str | None = None
        self._grid_x: float = 0.0
        self._grid_y: float = 0.0

        # Smoothed position (exponential moving average)
        self._smooth_x: float = 0.0
        self._smooth_y: float = 0.0

        # Pulse animation
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self.update)
        self._pulse_timer.start(50)

        self.setMinimumSize(200, 200)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_position(
        self,
        region_name: str | None,
        grid_x: float = 0.0,
        grid_y: float = 0.0,
    ) -> None:
        """Update the displayed region and player position."""
        if region_name is None:
            self._current_region = None
            self.update()
            return

        if region_name != self._current_region:
            # Region changed — snap immediately
            self._smooth_x = grid_x
            self._smooth_y = grid_y
        else:
            # Same region — exponential moving average to reduce jitter
            alpha = 0.3
            dx = grid_x - self._smooth_x
            dy = grid_y - self._smooth_y
            if abs(dx) > 0.005 or abs(dy) > 0.005:
                self._smooth_x += alpha * dx
                self._smooth_y += alpha * dy

        self._current_region = region_name
        self._grid_x = grid_x
        self._grid_y = grid_y
        self.update()

    def clear_cache(self) -> None:
        """Clear cached pixmaps so templates are reloaded from disk."""
        self._pixmap_cache.clear()
        self.update()

    # ------------------------------------------------------------------
    # Template loading
    # ------------------------------------------------------------------

    def _get_template_pixmap(self, region_name: str) -> QPixmap | None:
        if region_name in self._pixmap_cache:
            return self._pixmap_cache[region_name]
        path = self._templates_dir / f"{region_name}.png"
        if not path.exists():
            return None
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None
        self._pixmap_cache[region_name] = pixmap
        return pixmap

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(30, 30, 40))

        if self._current_region is None:
            self._draw_placeholder(painter, "No region detected")
            painter.end()
            return

        pixmap = self._get_template_pixmap(self._current_region)
        if pixmap is None:
            self._draw_placeholder(painter, f"No template for\n{self._current_region}")
            painter.end()
            return

        # Scale template to fit, preserving aspect ratio
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        dx = (self.width() - scaled.width()) / 2
        dy = (self.height() - scaled.height()) / 2
        painter.drawPixmap(int(dx), int(dy), scaled)

        # Clamp smoothed position to valid range
        sx = max(-0.5, min(0.5, self._smooth_x))
        sy = max(-0.5, min(0.5, self._smooth_y))

        # Map grid offset to pixel position on the scaled template
        marker_px = dx + scaled.width() * (0.5 + sx)
        marker_py = dy + scaled.height() * (0.5 + sy)

        # Pulsing green dot
        t = time.time()
        pulse = 0.5 + 0.5 * math.sin(t * 4)
        radius = 6 + 3 * pulse

        # Outer glow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 255, 80, int(100 * pulse))))
        painter.drawEllipse(QPointF(marker_px, marker_py), radius * 2, radius * 2)

        # Inner dot
        painter.setBrush(QBrush(QColor(0, 200, 60)))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(QPointF(marker_px, marker_py), radius, radius)

        # Region name label at top
        painter.setPen(QColor(220, 220, 220))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(0, 4, self.width(), 20),
            Qt.AlignmentFlag.AlignHCenter,
            self._current_region,
        )

        painter.end()

    def _draw_placeholder(self, painter: QPainter, text: str) -> None:
        painter.setPen(QColor(120, 120, 120))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
