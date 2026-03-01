from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Application configuration with sensible defaults."""

    # How often to capture and process the screen (milliseconds)
    capture_interval_ms: int = 500

    # Foxhole window title to search for
    window_title: str = "War"

    # Minimum confidence score (0-1) to accept a template match
    match_confidence_threshold: float = 0.7

    # Path to template images directory
    templates_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "assets" / "templates"
    )

    # Map widget settings
    hex_size: int = 50
    marker_radius: int = 8

    # Orange triangle/arrow detection HSV range
    triangle_hue_low: int = 10
    triangle_hue_high: int = 25
    triangle_sat_min: int = 150
    triangle_val_min: int = 180

    # Contour area bounds for the player marker
    triangle_min_area: int = 30
    triangle_max_area: int = 2000

    # Radius (pixels) to crop around the detected marker for template matching
    crop_radius: int = 200
