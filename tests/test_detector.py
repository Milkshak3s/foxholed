"""Tests for the position detection module."""

from __future__ import annotations

import numpy as np

from foxholed.config import Config
from foxholed.detector import Position, PositionDetector


def test_detect_returns_none_for_empty_frame() -> None:
    config = Config()
    detector = PositionDetector(config)
    assert detector.detect(np.empty((0, 0, 3), dtype=np.uint8)) is None


def test_detect_returns_none_for_blank_frame() -> None:
    config = Config()
    detector = PositionDetector(config)
    blank = np.zeros((100, 100, 3), dtype=np.uint8)
    assert detector.detect(blank) is None


def test_position_dataclass() -> None:
    pos = Position(region_name="Deadlands", grid_x=0.5, grid_y=-0.3, confidence=0.85)
    assert pos.region_name == "Deadlands"
    assert pos.confidence == 0.85
