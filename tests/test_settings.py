"""Tests for settings persistence."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from foxholed.config import Config, MinimapRegion
from foxholed.settings import load_settings, save_settings, reset_settings


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"

    with patch("foxholed.settings.SETTINGS_FILE", settings_file), \
         patch("foxholed.settings.SETTINGS_DIR", tmp_path):
        config = Config()
        config.window_title = "TestWindow"
        config.capture_interval_ms = 2000
        config.match_confidence_threshold = 0.8
        config.minimap_region = MinimapRegion(x=10, y=20, width=400, height=400)

        save_settings(
            config,
            window_geometry={"x": 100, "y": 200, "width": 800, "height": 600},
            map_view={"zoom": 2.0, "pan_x": 50.0, "pan_y": 60.0},
            always_on_top=True,
        )

        assert settings_file.exists()

        config2 = Config()
        saved = load_settings(config2)

        assert config2.window_title == "TestWindow"
        assert config2.capture_interval_ms == 2000
        assert config2.match_confidence_threshold == 0.8
        assert config2.minimap_region.x == 10
        assert config2.minimap_region.width == 400
        assert saved["always_on_top"] is True
        assert saved["window_geometry"]["x"] == 100
        assert saved["map_view"]["zoom"] == 2.0


def test_load_missing_file(tmp_path: Path) -> None:
    settings_file = tmp_path / "nonexistent.json"

    with patch("foxholed.settings.SETTINGS_FILE", settings_file):
        config = Config()
        saved = load_settings(config)
        assert saved == {}
        assert config.window_title == "War"  # default preserved


def test_reset_settings(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("{}")

    with patch("foxholed.settings.SETTINGS_FILE", settings_file):
        reset_settings()
        assert not settings_file.exists()


def test_load_corrupt_file(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("not valid json{{{")

    with patch("foxholed.settings.SETTINGS_FILE", settings_file):
        config = Config()
        saved = load_settings(config)
        assert saved == {}
