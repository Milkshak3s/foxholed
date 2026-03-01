"""Tests for the position detection module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np

from foxholed.config import Config
from foxholed.detector import Position, PositionDetector


def _make_orange_triangle(frame: np.ndarray, cx: int, cy: int, size: int = 15) -> None:
    """Draw a filled orange triangle on the frame at (cx, cy)."""
    pts = np.array([
        [cx, cy - size],
        [cx - size, cy + size],
        [cx + size, cy + size],
    ], dtype=np.int32)
    # Orange in BGR: B=0, G=165, R=255 → HSV ~15, 255, 255
    cv2.fillPoly(frame, [pts], (0, 165, 255))


# ------------------------------------------------------------------
# Position dataclass
# ------------------------------------------------------------------

def test_position_dataclass() -> None:
    pos = Position(region_name="Deadlands", grid_x=0.5, grid_y=-0.3, confidence=0.85)
    assert pos.region_name == "Deadlands"
    assert pos.confidence == 0.85


def test_position_method_default() -> None:
    pos = Position(region_name="Deadlands", grid_x=0.0, grid_y=0.0, confidence=0.9)
    assert pos.method == "template"


# ------------------------------------------------------------------
# Template loading
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# Triangle / arrow detection
# ------------------------------------------------------------------

def test_find_triangle_on_synthetic_frame() -> None:
    """An orange triangle drawn on a dark background should be detected."""
    config = Config()
    detector = PositionDetector(config)

    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    _make_orange_triangle(frame, 200, 200)

    result = detector.find_player_triangle(frame)
    assert result is not None
    cx, cy = result
    # Should be close to where we drew it
    assert abs(cx - 200) < 10
    assert abs(cy - 200) < 10


def test_find_triangle_returns_none_on_blank() -> None:
    """No orange pixels → no marker found."""
    config = Config()
    detector = PositionDetector(config)

    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    assert detector.find_player_triangle(frame) is None


def test_find_triangle_ignores_small_noise() -> None:
    """Tiny orange dots below min_area should be ignored."""
    config = Config()
    detector = PositionDetector(config)

    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    # Draw a single orange pixel (area=1, below min_area=30)
    frame[200, 200] = (0, 165, 255)
    assert detector.find_player_triangle(frame) is None


# ------------------------------------------------------------------
# Crop extraction
# ------------------------------------------------------------------

def test_crop_around_center() -> None:
    """Crop around center of frame should return correct dimensions."""
    config = Config(crop_radius=50)
    detector = PositionDetector(config)

    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    crop, (mx, my) = detector._crop_around(frame, 200, 200)

    assert crop.shape[0] == 100  # 2 * radius
    assert crop.shape[1] == 100
    assert mx == 50  # marker at center of crop
    assert my == 50


def test_crop_around_clamps_to_bounds() -> None:
    """Crop near edge should be clamped, marker offset adjusted."""
    config = Config(crop_radius=100)
    detector = PositionDetector(config)

    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    crop, (mx, my) = detector._crop_around(frame, 10, 10)

    # x1=0, y1=0 (clamped), x2=110, y2=110
    assert crop.shape[1] == 110
    assert crop.shape[0] == 110
    assert mx == 10  # marker at x=10 within crop
    assert my == 10


# ------------------------------------------------------------------
# Full pipeline: detect() returns None without triangle
# ------------------------------------------------------------------

def test_detect_returns_none_without_triangle() -> None:
    """No orange marker → detect returns None (map not open)."""
    config = Config()
    detector = PositionDetector(config)
    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    assert detector.detect(frame) is None


def test_detect_returns_none_for_empty_frame() -> None:
    config = Config()
    detector = PositionDetector(config)
    assert detector.detect(np.empty((0, 0, 3), dtype=np.uint8)) is None


# ------------------------------------------------------------------
# Full pipeline with template matching
# ------------------------------------------------------------------

def test_detect_with_triangle_and_template() -> None:
    """Orange triangle + matching template → valid Position with grid offsets."""
    # Create a distinctive background pattern
    frame = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.rectangle(frame, (150, 150), (350, 350), (255, 255, 255), -1)
    cv2.rectangle(frame, (200, 200), (300, 300), (128, 128, 128), -1)

    # Draw orange triangle at center
    _make_orange_triangle(frame, 250, 250)

    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir)
        # Save a crop of the frame as a template (without the triangle)
        template_frame = frame.copy()
        # Erase the triangle area to make a clean template
        cv2.rectangle(template_frame, (235, 235), (265, 265), (255, 255, 255), -1)
        crop_for_template = template_frame[150:350, 150:350]
        gray_template = cv2.cvtColor(crop_for_template, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(str(templates_dir / "Deadlands.png"), gray_template)

        config = Config(
            templates_dir=templates_dir,
            match_confidence_threshold=0.3,
            crop_radius=200,
        )
        detector = PositionDetector(config)
        assert detector.template_count == 1

        result = detector.detect(frame)
        assert result is not None
        assert result.region_name == "Deadlands"
        assert result.method == "template"
        assert -0.5 <= result.grid_x <= 0.5
        assert -0.5 <= result.grid_y <= 0.5
