"""Tests for the RegionViewWidget position logic.

These tests run headless by setting QT_QPA_PLATFORM=offscreen before
importing any Qt modules.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Must be set before any Qt import
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication

# QApplication must exist before any QWidget is created
_app = QApplication.instance() or QApplication([])

from foxholed.ui.region_view_widget import RegionViewWidget


def _make_templates_dir() -> tuple[tempfile.TemporaryDirectory, Path]:
    """Create a temp dir with a small template image."""
    tmpdir = tempfile.TemporaryDirectory()
    path = Path(tmpdir.name)
    img = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (80, 80), 255, -1)
    cv2.imwrite(str(path / "Deadlands.png"), img)
    return tmpdir, path


def test_update_position_stores_state() -> None:
    tmpdir, templates_dir = _make_templates_dir()
    widget = RegionViewWidget(templates_dir)

    widget.update_position("Deadlands", 0.1, -0.2)
    assert widget._current_region == "Deadlands"
    assert widget._smooth_x == 0.1
    assert widget._smooth_y == -0.2

    tmpdir.cleanup()


def test_smoothing_reduces_jitter() -> None:
    tmpdir, templates_dir = _make_templates_dir()
    widget = RegionViewWidget(templates_dir)

    widget.update_position("Deadlands", 0.1, 0.1)
    assert widget._smooth_x == 0.1

    # Small jitter — smoothed value should move less than raw delta
    widget.update_position("Deadlands", 0.12, 0.1)
    # alpha=0.3 → smooth_x += 0.3 * 0.02 = 0.006 → 0.106
    assert abs(widget._smooth_x - 0.106) < 0.001
    assert abs(widget._smooth_x - 0.1) < abs(0.12 - 0.1)

    tmpdir.cleanup()


def test_region_change_snaps() -> None:
    tmpdir, templates_dir = _make_templates_dir()
    widget = RegionViewWidget(templates_dir)

    widget.update_position("Deadlands", 0.1, 0.1)
    assert widget._smooth_x == 0.1

    # Switching region should snap, not smooth
    widget.update_position("Fishermans", 0.3, 0.4)
    assert widget._smooth_x == 0.3
    assert widget._smooth_y == 0.4

    tmpdir.cleanup()


def test_dead_zone_prevents_tiny_updates() -> None:
    tmpdir, templates_dir = _make_templates_dir()
    widget = RegionViewWidget(templates_dir)

    widget.update_position("Deadlands", 0.1, 0.1)

    # Delta of 0.001 is below dead zone of 0.005
    widget.update_position("Deadlands", 0.101, 0.101)
    assert widget._smooth_x == 0.1
    assert widget._smooth_y == 0.1

    tmpdir.cleanup()


def test_clear_cache() -> None:
    tmpdir, templates_dir = _make_templates_dir()
    widget = RegionViewWidget(templates_dir)

    pixmap = widget._get_template_pixmap("Deadlands")
    assert pixmap is not None
    assert "Deadlands" in widget._pixmap_cache

    widget.clear_cache()
    assert len(widget._pixmap_cache) == 0

    tmpdir.cleanup()


def test_none_position_clears_region() -> None:
    tmpdir, templates_dir = _make_templates_dir()
    widget = RegionViewWidget(templates_dir)

    widget.update_position("Deadlands", 0.1, 0.1)
    assert widget._current_region == "Deadlands"

    widget.update_position(None)
    assert widget._current_region is None

    tmpdir.cleanup()
