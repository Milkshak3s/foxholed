"""Compact floating overlay showing player position on a mini hex map."""

from __future__ import annotations

import math
import time

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from foxholed.map_data import REGIONS, hex_to_pixel


class OverlayWidget(QWidget):
    """Tiny frameless floating window showing the player marker on a mini map."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(220, 170)

        self._hex_size = 8
        self._player_col: float | None = None
        self._player_row: float | None = None
        self._drag_start: QPointF | None = None

        # Pulse animation
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self.update)
        self._pulse_timer.start(50)

    def update_position(self, region_name: str | None, grid_x: float | None = None, grid_y: float | None = None) -> None:
        if region_name is None:
            self._player_col = None
            self._player_row = None
        else:
            for r in REGIONS:
                if r.name == region_name:
                    self._player_col = r.col + (grid_x or 0)
                    self._player_row = r.row + (grid_y or 0)
                    break
        self.update()

    def _map_center(self) -> tuple[float, float]:
        xs, ys = [], []
        for r in REGIONS:
            px, py = hex_to_pixel(r.col, r.row, self._hex_size)
            xs.append(px)
            ys.append(py)
        return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)

    # Draggable
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition() - QPointF(self.pos())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_start is not None:
            self.move((event.globalPosition() - self._drag_start).toPoint())

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_start = None

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(20, 20, 30, 230))
        painter.setPen(QPen(QColor(80, 120, 80), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        cx, cy = self._map_center()
        ox = self.width() / 2 - cx
        oy = self.height() / 2 - cy

        # Draw tiny hexes
        hex_pen = QPen(QColor(60, 90, 60), 0.5)
        hex_brush = QBrush(QColor(40, 50, 40))

        for region in REGIONS:
            wx, wy = hex_to_pixel(region.col, region.row, self._hex_size)
            sx, sy = wx + ox, wy + oy
            poly = self._hex_polygon(sx, sy, self._hex_size * 0.9)
            painter.setPen(hex_pen)
            painter.setBrush(hex_brush)
            painter.drawPolygon(poly)

        # Draw player marker
        if self._player_col is not None and self._player_row is not None:
            wx, wy = hex_to_pixel(self._player_col, self._player_row, self._hex_size)
            sx, sy = wx + ox, wy + oy

            t = time.time()
            pulse = 0.5 + 0.5 * math.sin(t * 4)
            r = 3 + 2 * pulse

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 80, 80, int(100 * pulse))))
            painter.drawEllipse(QPointF(sx, sy), r * 1.5, r * 1.5)

            painter.setBrush(QBrush(QColor(255, 60, 60)))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawEllipse(QPointF(sx, sy), r, r)

        painter.end()

    def _hex_polygon(self, cx: float, cy: float, size: float) -> QPolygonF:
        points = []
        for i in range(6):
            angle = math.pi / 180 * (60 * i)
            px = cx + size * math.cos(angle)
            py = cy + size * math.sin(angle)
            points.append(QPointF(px, py))
        return QPolygonF(points)
