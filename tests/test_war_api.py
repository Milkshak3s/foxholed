"""Tests for the War API client."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from foxholed.war_api import fetch_faction_control, _API_TO_REGION


def test_api_to_region_mapping_covers_known_regions() -> None:
    """The API mapping should cover our core regions."""
    assert "Deadlands" in _API_TO_REGION.values()
    assert "The Heartlands" in _API_TO_REGION.values()
    assert "Oarbreaker Isles" in _API_TO_REGION.values()


def test_fetch_faction_control_handles_api_failure() -> None:
    """Should return empty dict on network failure."""
    with patch("foxholed.war_api._get_json", side_effect=Exception("network")):
        result = fetch_faction_control()
        assert result == {}


def test_fetch_faction_control_parses_teams() -> None:
    """Should correctly determine faction control from map items."""
    mock_maps = ["DeadLandsHex"]
    mock_dynamic = {
        "regionId": 1,
        "mapItems": [
            {"teamId": "COLONIALS", "iconType": 22, "x": 0.5, "y": 0.5, "flags": 0},
            {"teamId": "COLONIALS", "iconType": 22, "x": 0.3, "y": 0.3, "flags": 0},
            {"teamId": "WARDENS", "iconType": 22, "x": 0.7, "y": 0.7, "flags": 0},
        ],
        "lastUpdated": 0,
        "version": 1,
    }

    def mock_get_json(path: str) -> object:
        if path == "/worldconquest/maps":
            return mock_maps
        return mock_dynamic

    with patch("foxholed.war_api._get_json", side_effect=mock_get_json):
        result = fetch_faction_control()
        assert result.get("Deadlands") == "colonial"


def test_fetch_faction_control_neutral_when_no_items() -> None:
    """Regions with no map items should be neutral."""
    mock_maps = ["OriginHex"]
    mock_dynamic = {"regionId": 1, "mapItems": [], "lastUpdated": 0, "version": 1}

    def mock_get_json(path: str) -> object:
        if path == "/worldconquest/maps":
            return mock_maps
        return mock_dynamic

    with patch("foxholed.war_api._get_json", side_effect=mock_get_json):
        result = fetch_faction_control()
        assert result.get("Origin") == "neutral"
