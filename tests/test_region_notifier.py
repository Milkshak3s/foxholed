"""Tests for region change notifier."""

from __future__ import annotations

from unittest.mock import patch

from foxholed.region_notifier import RegionNotifier


def test_initial_region_no_notification() -> None:
    n = RegionNotifier()
    # First region set should not trigger (no "old" region to compare)
    result = n.update("Deadlands")
    assert result == "Deadlands"
    assert n.current_region == "Deadlands"


def test_same_region_no_change() -> None:
    n = RegionNotifier()
    n.update("Deadlands")
    result = n.update("Deadlands")
    assert result is None


def test_region_change_detected() -> None:
    n = RegionNotifier()
    n.update("Deadlands")
    with patch("foxholed.region_notifier.QApplication") as mock_app_cls:
        mock_app_cls.instance.return_value = mock_app_cls
        result = n.update("Origin")
        assert result == "Origin"
        mock_app_cls.beep.assert_called_once()


def test_none_region_ignored() -> None:
    n = RegionNotifier()
    n.update("Deadlands")
    result = n.update(None)
    assert result is None
    assert n.current_region == "Deadlands"
