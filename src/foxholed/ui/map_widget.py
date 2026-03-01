"""Custom QWidget that renders the Foxhole world hex map and a player marker."""

from __future__ import annotations

import math
import time

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF, QWheelEvent
from PyQt6.QtWidgets import QToolTip, QWidget

from foxholed.map_data import REGIONS, HexRegion, hex_to_pixel

_PAN_STEP = 40.0
_ZOOM_FACTOR = 1.15


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

        # Hover state
        self._hovered_region: str | None = None

        # Faction control overlay: region_name -> "colonial" | "warden" | "neutral"
        self._faction_control: dict[str, str] = {}

        # Position history trail (list of (col, row) tuples)
        self._position_trail: list[tuple[float, float]] = []
        self._max_trail_length = 50

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
            for r in REGIONS:
                if r.name == region_name:
                    col = r.col + (grid_x or 0)
                    row = r.row + (grid_y or 0)
                    self._player_col = col
                    self._player_row = row
                    # Add to trail
                    if (
                        not self._position_trail
                        or self._position_trail[-1] != (col, row)
                    ):
                        self._position_trail.append((col, row))
                        if len(self._position_trail) > self._max_trail_length:
                            self._position_trail.pop(0)
                    break
        self.update()

    def set_faction_control(self, control: dict[str, str]) -> None:
        """Set faction control data: region_name -> 'colonial'|'warden'|'neutral'."""
        self._faction_control = control
        self.update()

    def center_on_player(self) -> None:
        """Center the view on the player marker."""
        if self._player_col is None or self._player_row is None:
            return
        wx, wy = hex_to_pixel(self._player_col, self._player_row, self.hex_size)
        self._pan = QPointF(
            self.width() / 2 - wx * self._zoom,
            self.height() / 2 - wy * self._zoom,
        )
        self.update()

    def reset_view(self) -> None:
        """Reset zoom to 1.0 and re-center."""
        self._zoom = 1.0
        self._center_view()
        self.update()

    def zoom_in(self) -> None:
        self._zoom = min(5.0, self._zoom * _ZOOM_FACTOR)
        self.update()

    def zoom_out(self) -> None:
        self._zoom = max(0.2, self._zoom / _ZOOM_FACTOR)
        self.update()

    def pan_left(self) -> None:
        self._pan += QPointF(_PAN_STEP, 0)
        self.update()

    def pan_right(self) -> None:
        self._pan += QPointF(-_PAN_STEP, 0)
        self.update()

    def pan_up(self) -> None:
        self._pan += QPointF(0, _PAN_STEP)
        self.update()

    def pan_down(self) -> None:
        self._pan += QPointF(0, -_PAN_STEP)
        self.update()

    def get_view_state(self) -> dict:
        """Return the current zoom/pan state for persistence."""
        return {"zoom": self._zoom, "pan_x": self._pan.x(), "pan_y": self._pan.y()}

    def restore_view_state(self, state: dict) -> None:
        """Restore zoom/pan from saved state."""
        if "zoom" in state:
            self._zoom = state["zoom"]
        if "pan_x" in state and "pan_y" in state:
            self._pan = QPointF(state["pan_x"], state["pan_y"])
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

    def _screen_to_world(self, sx: float, sy: float) -> QPointF:
        return QPointF((sx - self._pan.x()) / self._zoom, (sy - self._pan.y()) / self._zoom)

    def _hit_test_region(self, screen_pos: QPointF) -> str | None:
        """Return the region name under the given screen position, or None."""
        wp = self._screen_to_world(screen_pos.x(), screen_pos.y())
        best_dist = float("inf")
        best_name: str | None = None
        threshold = self.hex_size * 0.95

        for region in REGIONS:
            rx, ry = hex_to_pixel(region.col, region.row, self.hex_size)
            dist = math.hypot(wp.x() - rx, wp.y() - ry)
            if dist < threshold and dist < best_dist:
                best_dist = dist
                best_name = region.name

        return best_name

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._center_view()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        mouse_pos = event.position()
        old_zoom = self._zoom

        factor = _ZOOM_FACTOR if event.angleDelta().y() > 0 else 1 / _ZOOM_FACTOR
        self._zoom = max(0.2, min(5.0, self._zoom * factor))

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
        else:
            # Hover detection
            region = self._hit_test_region(event.position())
            if region != self._hovered_region:
                self._hovered_region = region
                self.update()
            if region:
                QToolTip.showText(event.globalPosition().toPoint(), region, self)
            else:
                QToolTip.hideText()

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
        self._draw_position_trail(painter)
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

    def _get_hex_fill(self, region: HexRegion) -> QBrush:
        """Get the fill brush for a hex, considering faction control and hover."""
        faction = self._faction_control.get(region.name)
        if faction == "colonial":
            base = QColor(45, 80, 45)
        elif faction == "warden":
            base = QColor(45, 55, 90)
        elif faction == "neutral":
            base = QColor(70, 70, 60)
        else:
            base = QColor(45, 55, 45)

        if region.name == self._hovered_region:
            base = base.lighter(130)

        return QBrush(base)

    def _draw_hex_grid(self, painter: QPainter) -> None:
        hex_pen = QPen(QColor(80, 120, 80), 1.5)
        text_color = QColor(180, 200, 180)

        for region in REGIONS:
            wx, wy = hex_to_pixel(region.col, region.row, self.hex_size)
            sp = self._world_to_screen(wx, wy)

            scaled_size = self.hex_size * self._zoom * 0.95
            poly = self._hex_polygon(sp.x(), sp.y(), scaled_size)

            painter.setPen(hex_pen)
            painter.setBrush(self._get_hex_fill(region))
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

    def _draw_position_trail(self, painter: QPainter) -> None:
        """Draw fading dots for the position history trail."""
        count = len(self._position_trail)
        if count < 2:
            return

        for i, (col, row) in enumerate(self._position_trail[:-1]):
            wx, wy = hex_to_pixel(col, row, self.hex_size)
            sp = self._world_to_screen(wx, wy)

            alpha = int(40 + 120 * (i / count))
            radius = max(2, 4 * self._zoom * (0.5 + 0.5 * i / count))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 120, 80, alpha)))
            painter.drawEllipse(sp, radius, radius)

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
