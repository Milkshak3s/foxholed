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


def test_position_method_default() -> None:
    pos = Position(region_name="Deadlands", grid_x=0.0, grid_y=0.0, confidence=0.9)
    assert pos.method == "template"


def test_position_method_ocr() -> None:
    pos = Position(region_name="Deadlands", grid_x=0.0, grid_y=0.0, confidence=0.5, method="ocr")
    assert pos.method == "ocr"


def test_template_count_empty() -> None:
    config = Config()
    detector = PositionDetector(config)
    assert detector.template_count >= 0


def test_reload_templates() -> None:
    config = Config()
    detector = PositionDetector(config)
    initial = detector.template_count
    detector.reload_templates()
    assert detector.template_count == initial


def test_grid_offsets_range() -> None:
    """When a template matches, grid_x and grid_y should be in [-0.5, 0.5]."""
    import cv2
    import tempfile
    from pathlib import Path

    # Create a small "minimap" frame with a known pattern
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    # Draw a distinctive pattern in the center
    cv2.rectangle(frame, (80, 80), (120, 120), (255, 255, 255), -1)

    # Save the pattern as a template
    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir)
        template = cv2.cvtColor(frame[80:120, 80:120], cv2.COLOR_BGR2GRAY)
        cv2.imwrite(str(templates_dir / "Deadlands.png"), template)

        config = Config(templates_dir=templates_dir, match_confidence_threshold=0.5)
        detector = PositionDetector(config)
        assert detector.template_count == 1

        result = detector.detect(frame)
        assert result is not None
        assert result.region_name == "Deadlands"
        assert result.method == "template"
        # Center of template placed at center of frame → offsets near 0
        assert -0.5 <= result.grid_x <= 0.5
        assert -0.5 <= result.grid_y <= 0.5
