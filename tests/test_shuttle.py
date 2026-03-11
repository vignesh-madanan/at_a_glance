"""Tests for services/shuttle.py"""
import datetime
import pytest
from unittest.mock import patch, MagicMock
import pytz


NYC_TZ = pytz.timezone('America/New_York')


class TestShuttleServiceGetNextShuttleTimes:
    def test_returns_three_dashes_for_invalid_location(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_next_shuttle_times("Invalid Location")
        assert result == ["--", "--", "--"]

    def test_returns_list_of_three(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_next_shuttle_times("10 Halletts Point")
        assert len(result) == 3

    def test_returns_strings(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_next_shuttle_times("10 Halletts Point")
        for item in result:
            assert isinstance(item, str)

    def test_returns_future_times_in_morning(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        # Mock current time at 6:00 AM
        mock_now = MagicMock()
        mock_now.hour = 6
        mock_now.minute = 0
        with patch('services.shuttle.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            result = svc.get_next_shuttle_times("10 Halletts Point")
        assert len(result) == 3
        # At 6:00 AM, next times should be 6:30 AM, 7:00 AM, 7:30 AM
        assert "6:30 AM" in result
        assert "7:00 AM" in result
        assert "7:30 AM" in result

    def test_returns_next_day_times_at_end_of_day(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        # Mock current time at 8:00 PM (after last shuttle at 7:30 PM)
        mock_now = MagicMock()
        mock_now.hour = 20
        mock_now.minute = 0
        with patch('services.shuttle.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            result = svc.get_next_shuttle_times("10 Halletts Point")
        assert len(result) == 3
        # All results should be "Next Day" entries
        for item in result:
            assert "(Next Day)" in item

    def test_returns_mix_of_today_and_next_day_near_end_of_day(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        # Mock current time at 7:00 PM (last shuttle is 7:30 PM)
        mock_now = MagicMock()
        mock_now.hour = 19
        mock_now.minute = 0
        with patch('services.shuttle.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            result = svc.get_next_shuttle_times("10 Halletts Point")
        assert len(result) == 3
        # Should have "7:30 PM" and then Next Day entries
        assert "7:30 PM" in result

    def test_halletts_point_location(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_next_shuttle_times("10 Halletts Point")
        assert len(result) == 3

    def test_30th_ave_location(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_next_shuttle_times("30th Ave & 31st St")
        assert len(result) == 3

    def test_30th_ave_times_offset_from_halletts(self):
        from services.shuttle import ShuttleService
        from services.config import SHUTTLE_TIMING
        svc = ShuttleService()
        # 30th Ave times are 15 minutes after Halletts Point times
        halletts_times = SHUTTLE_TIMING["10 Halletts Point"]
        thirteenth_times = SHUTTLE_TIMING["30th Ave & 31st St"]
        # First time: Halletts is 5:30 AM, 30th Ave is 5:45 AM
        assert halletts_times[0] == "5:30 AM"
        assert thirteenth_times[0] == "5:45 AM"

    def test_returns_exactly_three_items_always(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        # Test at different times
        for hour in [0, 6, 12, 18, 23]:
            mock_now = MagicMock()
            mock_now.hour = hour
            mock_now.minute = 0
            with patch('services.shuttle.datetime') as mock_dt:
                mock_dt.datetime.now.return_value = mock_now
                mock_dt.datetime.strptime = datetime.datetime.strptime
                result = svc.get_next_shuttle_times("10 Halletts Point")
            assert len(result) == 3, f"Expected 3 items at hour {hour}, got {len(result)}"

    def test_first_time_at_midnight(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        mock_now = MagicMock()
        mock_now.hour = 0
        mock_now.minute = 0
        with patch('services.shuttle.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            result = svc.get_next_shuttle_times("10 Halletts Point")
        assert len(result) == 3
        # All times should be future (5:30 AM is first)
        assert "5:30 AM" in result


class TestShuttleServiceGetShuttleArrivals:
    def test_returns_dict(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_shuttle_arrivals()
        assert isinstance(result, dict)

    def test_contains_halletts_point(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_shuttle_arrivals()
        assert "10 Halletts Point" in result

    def test_halletts_point_has_three_times(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_shuttle_arrivals()
        assert len(result["10 Halletts Point"]) == 3

    def test_halletts_point_values_are_strings(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_shuttle_arrivals()
        for item in result["10 Halletts Point"]:
            assert isinstance(item, str)

    def test_only_returns_halletts_point(self):
        from services.shuttle import ShuttleService
        svc = ShuttleService()
        result = svc.get_shuttle_arrivals()
        assert list(result.keys()) == ["10 Halletts Point"]
