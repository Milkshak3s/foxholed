"""Custom QWidget that renders the Foxhole world hex map and a player marker."""

from __future__ import annotations

import math
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF, QWheelEvent
from PyQt6.QtWidgets import QWidget

from foxholed.map_data import REGIONS, HexRegion, hex_to_pixel


class MapWidget(QWidget):
    """Hex-grid map with zoom, pan, and a pulsing player marker."""

    def __init__(self, hex_size: int = 50, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.hex_size = hex_size

        # View transform state
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._drag_start: QPointF | None = None
        self._pan_at_drag_start = QPointF(0, 0)

        # Player position (hex col/row, or None if unknown)
        self._player_col: float | None = None
        self._player_row: float | None = None
        self._player_region: str | None = None

        # Pulse animation
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self.update)
        self._pulse_timer.start(50)

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

        # Center the view on startup
        self._center_view()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_position(
        self,
        region_name: str | None,
        grid_x: float | None = None,
        grid_y: float | None = None,
    ) -> None:
        """Update the player marker position on the map."""
        self._player_region = region_name
        if region_name is None:
            self._player_col = None
            self._player_row = None
        else:
            # Find the region and offset by sub-grid position
            for r in REGIONS:
                if r.name == region_name:
                    self._player_col = r.col + (grid_x or 0)
                    self._player_row = r.row + (grid_y or 0)
                    break
        self.update()

    # ------------------------------------------------------------------
    # View helpers
    # ------------------------------------------------------------------

    def _center_view(self) -> None:
        """Center the view on the middle of all regions."""
        if not REGIONS:
            return
        xs, ys = [], []
        for r in REGIONS:
            px, py = hex_to_pixel(r.col, r.row, self.hex_size)
            xs.append(px)
            ys.append(py)
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        self._pan = QPointF(
            self.width() / 2 - cx * self._zoom,
            self.height() / 2 - cy * self._zoom,
        )

    def _world_to_screen(self, wx: float, wy: float) -> QPointF:
        return QPointF(wx * self._zoom + self._pan.x(), wy * self._zoom + self._pan.y())

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._center_view()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        mouse_pos = event.position()
        old_zoom = self._zoom

        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom = max(0.2, min(5.0, self._zoom * factor))

        # Zoom toward mouse position
        ratio = self._zoom / old_zoom
        self._pan = QPointF(
            mouse_pos.x() - ratio * (mouse_pos.x() - self._pan.x()),
            mouse_pos.y() - ratio * (mouse_pos.y() - self._pan.y()),
        )
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position()
            self._pan_at_drag_start = QPointF(self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_start is not None:
            delta = event.position() - self._drag_start
            self._pan = self._pan_at_drag_start + delta
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 40))

        self._draw_hex_grid(painter)
        self._draw_player_marker(painter)

        painter.end()

    def _hex_polygon(self, cx: float, cy: float, size: float) -> QPolygonF:
        """Create a flat-top hexagon polygon centered at (cx, cy)."""
        points = []
        for i in range(6):
            angle = math.pi / 180 * (60 * i)
            px = cx + size * math.cos(angle)
            py = cy + size * math.sin(angle)
            points.append(QPointF(px, py))
        return QPolygonF(points)

    def _draw_hex_grid(self, painter: QPainter) -> None:
        hex_pen = QPen(QColor(80, 120, 80), 1.5)
        hex_brush = QBrush(QColor(45, 55, 45))
        text_color = QColor(180, 200, 180)

        for region in REGIONS:
            wx, wy = hex_to_pixel(region.col, region.row, self.hex_size)
            sp = self._world_to_screen(wx, wy)

            scaled_size = self.hex_size * self._zoom * 0.95
            poly = self._hex_polygon(sp.x(), sp.y(), scaled_size)

            painter.setPen(hex_pen)
            painter.setBrush(hex_brush)
            painter.drawPolygon(poly)

            # Region label
            if self._zoom > 0.5:
                painter.setPen(QPen(text_color))
                font = painter.font()
                font.setPointSizeF(max(6, 8 * self._zoom))
                painter.setFont(font)
                rect = QRectF(
                    sp.x() - scaled_size * 0.8,
                    sp.y() - scaled_size * 0.3,
                    scaled_size * 1.6,
                    scaled_size * 0.6,
                )
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, region.name)

    def _draw_player_marker(self, painter: QPainter) -> None:
        if self._player_col is None or self._player_row is None:
            return

        wx, wy = hex_to_pixel(self._player_col, self._player_row, self.hex_size)
        sp = self._world_to_screen(wx, wy)

        # Pulsing effect
        t = time.time()
        pulse = 0.5 + 0.5 * math.sin(t * 4)
        radius = (8 + 4 * pulse) * self._zoom

        # Outer glow
        glow_color = QColor(255, 80, 80, int(100 * pulse))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow_color))
        painter.drawEllipse(sp, radius * 2, radius * 2)

        # Inner dot
        painter.setBrush(QBrush(QColor(255, 60, 60)))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(sp, radius, radius)
