from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MinimapRegion:
    """Pixel offsets for the minimap region within the game window."""

    x: int = 0
    y: int = 0
    width: int = 300
    height: int = 300


@dataclass
class Config:
    """Application configuration with sensible defaults."""

    # How often to capture and process the screen (milliseconds)
    capture_interval_ms: int = 1000

    # Foxhole window title to search for
    window_title: str = "War"

    # Minimap crop region relative to the game window
    minimap_region: MinimapRegion = field(default_factory=MinimapRegion)

    # Minimum confidence score (0-1) to accept a template match
    match_confidence_threshold: float = 0.7

    # Path to template images directory
    templates_dir: Path = Path("assets/templates")

    # Map widget settings
    hex_size: int = 50
    marker_radius: int = 8
