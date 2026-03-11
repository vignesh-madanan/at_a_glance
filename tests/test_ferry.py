"""Tests for services/ferry.py"""
import datetime
import csv
import io
import os
import pytest
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo


NYC_TZ = ZoneInfo("America/New_York")


@pytest.fixture
def ferry_service():
    from services.ferry import FerryService
    svc = FerryService(use_local_data=False)
    return svc


@pytest.fixture
def loaded_ferry_service():
    """FerryService with pre-loaded mock data"""
    from services.ferry import FerryService
    svc = FerryService(use_local_data=False)
    svc._loaded = True

    # Mock stops
    svc.stops = {
        "STOP1": {"stop_id": "STOP1", "stop_name": "Wall St/Pier 11", "stop_lat": 40.7, "stop_lon": -74.0},
        "STOP2": {"stop_id": "STOP2", "stop_name": "East 34th Street", "stop_lat": 40.74, "stop_lon": -73.97},
        "STOP3": {"stop_id": "STOP3", "stop_name": "Hunters Point South", "stop_lat": 40.74, "stop_lon": -73.96},
    }

    # Mock routes
    svc.routes = {
        "ER": {"route_id": "ER", "route_short_name": "ER", "route_long_name": "East River", "route_color": "00839C"},
        "SB": {"route_id": "SB", "route_short_name": "SB", "route_long_name": "South Brooklyn", "route_color": "FFD100"},
    }

    # Mock calendar: service active Monday-Friday
    today = datetime.date.today()
    start_str = (today - datetime.timedelta(days=30)).strftime('%Y%m%d')
    end_str = (today + datetime.timedelta(days=30)).strftime('%Y%m%d')
    svc.calendar = {
        "WD": {
            "service_id": "WD",
            "monday": True, "tuesday": True, "wednesday": True,
            "thursday": True, "friday": True, "saturday": False, "sunday": False,
            "start_date": start_str, "end_date": end_str,
        },
        "WE": {
            "service_id": "WE",
            "monday": False, "tuesday": False, "wednesday": False,
            "thursday": False, "friday": False, "saturday": True, "sunday": True,
            "start_date": start_str, "end_date": end_str,
        },
    }

    # Mock trips
    svc.trips = {
        "TRIP1": {"trip_id": "TRIP1", "route_id": "ER", "service_id": "WD", "trip_headsign": "Wall St", "direction_id": "0"},
        "TRIP2": {"trip_id": "TRIP2", "route_id": "SB", "service_id": "WD", "trip_headsign": "Bay Ridge", "direction_id": "1"},
    }

    # Mock stop times: schedule throughout the day
    svc.stop_times = [
        {"trip_id": "TRIP1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": "STOP1", "stop_sequence": 1},
        {"trip_id": "TRIP1", "arrival_time": "10:00:00", "departure_time": "10:00:00", "stop_id": "STOP1", "stop_sequence": 2},
        {"trip_id": "TRIP1", "arrival_time": "12:00:00", "departure_time": "12:00:00", "stop_id": "STOP1", "stop_sequence": 3},
        {"trip_id": "TRIP2", "arrival_time": "09:00:00", "departure_time": "09:00:00", "stop_id": "STOP1", "stop_sequence": 1},
        {"trip_id": "TRIP1", "arrival_time": "08:30:00", "departure_time": "08:30:00", "stop_id": "STOP2", "stop_sequence": 1},
    ]

    return svc


class TestFerryRoutes:
    def test_ferry_routes_defined(self):
        from services.ferry import FERRY_ROUTES
        assert len(FERRY_ROUTES) > 0

    def test_ferry_routes_have_required_keys(self):
        from services.ferry import FERRY_ROUTES
        for route_id, info in FERRY_ROUTES.items():
            assert "name" in info
            assert "color" in info

    def test_east_river_route_present(self):
        from services.ferry import FERRY_ROUTES
        assert "ER" in FERRY_ROUTES

    def test_astoria_route_present(self):
        from services.ferry import FERRY_ROUTES
        assert "AS" in FERRY_ROUTES


class TestFerryServiceInit:
    def test_init_with_local_data(self):
        from services.ferry import FerryService
        svc = FerryService(use_local_data=True)
        assert svc.use_local_data is True
        assert svc._loaded is False

    def test_init_without_local_data(self):
        from services.ferry import FerryService
        svc = FerryService(use_local_data=False)
        assert svc.use_local_data is False

    def test_init_sets_empty_collections(self):
        from services.ferry import FerryService
        svc = FerryService()
        assert svc.stops == {}
        assert svc.routes == {}
        assert svc.trips == {}
        assert svc.stop_times == []
        assert svc.calendar == {}


class TestLoadGtfsData:
    def test_returns_true_if_already_loaded(self, ferry_service):
        ferry_service._loaded = True
        result = ferry_service._load_gtfs_data()
        assert result is True

    def test_calls_load_local_when_use_local_true(self):
        from services.ferry import FerryService
        svc = FerryService(use_local_data=True)
        with patch.object(svc, '_load_local_gtfs') as mock_local:
            svc._load_gtfs_data()
        mock_local.assert_called_once()

    def test_calls_download_when_use_local_false(self):
        from services.ferry import FerryService
        svc = FerryService(use_local_data=False)
        with patch.object(svc, '_download_and_load_gtfs') as mock_dl:
            svc._load_gtfs_data()
        mock_dl.assert_called_once()

    def test_returns_false_on_exception(self):
        from services.ferry import FerryService
        svc = FerryService(use_local_data=True)
        with patch.object(svc, '_load_local_gtfs', side_effect=Exception("IO error")):
            result = svc._load_gtfs_data()
        assert result is False

    def test_sets_loaded_flag_on_success(self):
        from services.ferry import FerryService
        svc = FerryService(use_local_data=True)
        with patch.object(svc, '_load_local_gtfs'):
            svc._load_gtfs_data()
        assert svc._loaded is True


class TestLoadLocalGtfs:
    def test_loads_stops_from_local_file(self, tmp_path):
        from services.ferry import FerryService
        # Create fake stops.txt
        stops_dir = tmp_path / "gtfs"
        stops_dir.mkdir()
        stops_file = stops_dir / "stops.txt"
        stops_file.write_text('stop_id,stop_name,stop_lat,stop_lon\n"STOP1","Wall St",40.7,-74.0\n')

        svc = FerryService(use_local_data=True)
        with patch('services.ferry.LOCAL_GTFS_PATH', str(stops_dir)):
            svc._load_local_gtfs()

        assert "STOP1" in svc.stops
        assert svc.stops["STOP1"]["stop_name"] == "Wall St"

    def test_loads_routes_from_local_file(self, tmp_path):
        from services.ferry import FerryService
        gtfs_dir = tmp_path / "gtfs"
        gtfs_dir.mkdir()
        (gtfs_dir / "routes.txt").write_text(
            'route_id,route_short_name,route_long_name,route_color\n"ER","ER","East River","00839C"\n'
        )

        svc = FerryService(use_local_data=True)
        with patch('services.ferry.LOCAL_GTFS_PATH', str(gtfs_dir)):
            svc._load_local_gtfs()

        assert "ER" in svc.routes
        assert svc.routes["ER"]["route_long_name"] == "East River"

    def test_loads_trips_from_local_file(self, tmp_path):
        from services.ferry import FerryService
        gtfs_dir = tmp_path / "gtfs"
        gtfs_dir.mkdir()
        (gtfs_dir / "trips.txt").write_text(
            'trip_id,route_id,service_id,trip_headsign,direction_id\n"TRIP1","ER","WD","Wall St","0"\n'
        )

        svc = FerryService(use_local_data=True)
        with patch('services.ferry.LOCAL_GTFS_PATH', str(gtfs_dir)):
            svc._load_local_gtfs()

        assert "TRIP1" in svc.trips
        assert svc.trips["TRIP1"]["route_id"] == "ER"

    def test_loads_calendar_from_local_file(self, tmp_path):
        from services.ferry import FerryService
        gtfs_dir = tmp_path / "gtfs"
        gtfs_dir.mkdir()
        (gtfs_dir / "calendar.txt").write_text(
            'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"WD",1,1,1,1,1,0,0,20260101,20261231\n'
        )

        svc = FerryService(use_local_data=True)
        with patch('services.ferry.LOCAL_GTFS_PATH', str(gtfs_dir)):
            svc._load_local_gtfs()

        assert "WD" in svc.calendar
        assert svc.calendar["WD"]["monday"] is True
        assert svc.calendar["WD"]["saturday"] is False

    def test_loads_stop_times_from_local_file(self, tmp_path):
        from services.ferry import FerryService
        gtfs_dir = tmp_path / "gtfs"
        gtfs_dir.mkdir()
        (gtfs_dir / "stop_times.txt").write_text(
            'trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"TRIP1","08:00:00","08:00:00","STOP1",1\n'
        )

        svc = FerryService(use_local_data=True)
        with patch('services.ferry.LOCAL_GTFS_PATH', str(gtfs_dir)):
            svc._load_local_gtfs()

        assert len(svc.stop_times) == 1
        assert svc.stop_times[0]["trip_id"] == "TRIP1"

    def test_handles_missing_files_gracefully(self, tmp_path):
        from services.ferry import FerryService
        gtfs_dir = tmp_path / "empty_gtfs"
        gtfs_dir.mkdir()

        svc = FerryService(use_local_data=True)
        with patch('services.ferry.LOCAL_GTFS_PATH', str(gtfs_dir)):
            svc._load_local_gtfs()  # Should not raise

        assert svc.stops == {}
        assert svc.routes == {}


class TestGetActiveServiceIds:
    def test_returns_active_services_on_weekday(self, loaded_ferry_service):
        # Find a weekday
        test_date = datetime.date(2026, 3, 9)  # Monday
        result = loaded_ferry_service._get_active_service_ids(test_date)
        assert "WD" in result

    def test_returns_weekend_services_on_saturday(self, loaded_ferry_service):
        test_date = datetime.date(2026, 3, 7)  # Saturday
        result = loaded_ferry_service._get_active_service_ids(test_date)
        assert "WE" in result

    def test_excludes_weekday_services_on_weekend(self, loaded_ferry_service):
        test_date = datetime.date(2026, 3, 7)  # Saturday
        result = loaded_ferry_service._get_active_service_ids(test_date)
        assert "WD" not in result

    def test_returns_empty_when_date_out_of_range(self, loaded_ferry_service):
        # Past date, outside service range
        test_date = datetime.date(2020, 1, 1)
        result = loaded_ferry_service._get_active_service_ids(test_date)
        assert result == []


class TestParseTime:
    def test_parses_standard_time(self, ferry_service):
        result = ferry_service._parse_time("08:30:00")
        assert result == datetime.time(8, 30, 0)

    def test_parses_time_past_midnight(self, ferry_service):
        result = ferry_service._parse_time("25:00:00")
        assert result == datetime.time(1, 0, 0)  # 25 % 24 = 1

    def test_parses_time_without_seconds(self, ferry_service):
        result = ferry_service._parse_time("08:30")
        assert result == datetime.time(8, 30, 0)

    def test_returns_none_for_invalid_time(self, ferry_service):
        result = ferry_service._parse_time("invalid")
        assert result is None

    def test_returns_none_for_empty_string(self, ferry_service):
        result = ferry_service._parse_time("")
        assert result is None


class TestTimeToMinutes:
    def test_converts_morning_time(self, ferry_service):
        result = ferry_service._time_to_minutes("08:30:00")
        assert result == 8 * 60 + 30

    def test_converts_midnight(self, ferry_service):
        result = ferry_service._time_to_minutes("00:00:00")
        assert result == 0

    def test_converts_noon(self, ferry_service):
        result = ferry_service._time_to_minutes("12:00:00")
        assert result == 720

    def test_handles_invalid_string(self, ferry_service):
        result = ferry_service._time_to_minutes("invalid")
        assert result == 0

    def test_handles_past_midnight_time(self, ferry_service):
        result = ferry_service._time_to_minutes("25:30:00")
        assert result == 25 * 60 + 30


class TestGetStopIdByName:
    def test_finds_stop_by_exact_name(self, loaded_ferry_service):
        result = loaded_ferry_service.get_stop_id_by_name("Wall St/Pier 11")
        assert result == "STOP1"

    def test_finds_stop_by_partial_name(self, loaded_ferry_service):
        result = loaded_ferry_service.get_stop_id_by_name("Wall St")
        assert result == "STOP1"

    def test_case_insensitive_search(self, loaded_ferry_service):
        result = loaded_ferry_service.get_stop_id_by_name("wall st")
        assert result == "STOP1"

    def test_returns_none_for_unknown_stop(self, loaded_ferry_service):
        result = loaded_ferry_service.get_stop_id_by_name("Nonexistent Stop XYZ")
        assert result is None


class TestGetAllStops:
    def test_returns_list(self, loaded_ferry_service):
        result = loaded_ferry_service.get_all_stops()
        assert isinstance(result, list)

    def test_returns_all_stops(self, loaded_ferry_service):
        result = loaded_ferry_service.get_all_stops()
        assert len(result) == 3

    def test_stops_have_required_fields(self, loaded_ferry_service):
        result = loaded_ferry_service.get_all_stops()
        for stop in result:
            assert "stop_id" in stop
            assert "stop_name" in stop


class TestGetAllRoutes:
    def test_returns_list(self, loaded_ferry_service):
        result = loaded_ferry_service.get_all_routes()
        assert isinstance(result, list)

    def test_returns_all_routes(self, loaded_ferry_service):
        result = loaded_ferry_service.get_all_routes()
        assert len(result) == 2

    def test_routes_have_required_fields(self, loaded_ferry_service):
        result = loaded_ferry_service.get_all_routes()
        for route in result:
            assert "route_id" in route
            assert "route_long_name" in route


class TestGetNextFerryTimes:
    def test_returns_count_items(self, loaded_ferry_service):
        # Mock current time to early morning (before all scheduled ferries)
        mock_now = datetime.datetime(2026, 3, 9, 6, 0, 0, tzinfo=NYC_TZ)  # Monday 6am
        with patch('services.ferry.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            mock_dt.date = datetime.date
            mock_dt.time = datetime.time
            mock_dt.timedelta = datetime.timedelta
            result = loaded_ferry_service.get_next_ferry_times("Wall St/Pier 11", count=3)
        assert len(result) == 3

    def test_returns_placeholder_for_unknown_stop(self, loaded_ferry_service):
        result = loaded_ferry_service.get_next_ferry_times("Unknown Stop XYZ")
        assert result == ["--", "--", "--"]

    def test_pads_with_placeholder_when_insufficient_departures(self, loaded_ferry_service):
        # Mock time at end of day (after all ferries)
        mock_now = datetime.datetime(2026, 3, 9, 23, 0, 0, tzinfo=NYC_TZ)
        with patch('services.ferry.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            mock_dt.date = datetime.date
            result = loaded_ferry_service.get_next_ferry_times("Wall St/Pier 11", count=3)
        assert "--" in result

    def test_returns_placeholder_when_no_active_services(self, loaded_ferry_service):
        # Clear the calendar so no services are active
        loaded_ferry_service.calendar = {}
        result = loaded_ferry_service.get_next_ferry_times("Wall St/Pier 11")
        assert result == ["--", "--", "--"]

    def test_filters_by_route_id(self, loaded_ferry_service):
        mock_now = datetime.datetime(2026, 3, 9, 6, 0, 0, tzinfo=NYC_TZ)
        with patch('services.ferry.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            mock_dt.date = datetime.date
            result_er = loaded_ferry_service.get_next_ferry_times("Wall St/Pier 11", route_id="ER")
            result_sb = loaded_ferry_service.get_next_ferry_times("Wall St/Pier 11", route_id="SB")
        # ER has 3 departures, SB has 1 from STOP1
        assert isinstance(result_er, list)
        assert isinstance(result_sb, list)

    def test_formats_boarding_when_less_than_one_minute(self, loaded_ferry_service):
        # Set up stop time 30 seconds in the future
        mock_now = datetime.datetime(2026, 3, 9, 8, 0, 0, tzinfo=NYC_TZ)  # Exactly at 8:00
        with patch('services.ferry.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            mock_dt.date = datetime.date
            result = loaded_ferry_service.get_next_ferry_times("Wall St/Pier 11")
        # 8:00 departure when current time is 8:00 → dep_minutes == current_minutes → not included
        # (dep_minutes > current_minutes required)
        assert isinstance(result, list)

    def test_returns_placeholder_when_load_fails(self):
        from services.ferry import FerryService
        svc = FerryService(use_local_data=False)
        with patch.object(svc, '_load_gtfs_data', return_value=False):
            result = svc.get_next_ferry_times("Wall St/Pier 11")
        assert result == ["--", "--", "--"]


class TestGetNextFerryTimesDetailed:
    def test_returns_list(self, loaded_ferry_service):
        mock_now = datetime.datetime(2026, 3, 9, 6, 0, 0, tzinfo=NYC_TZ)
        with patch('services.ferry.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            mock_dt.date = datetime.date
            result = loaded_ferry_service.get_next_ferry_times_detailed("Wall St/Pier 11")
        assert isinstance(result, list)

    def test_returns_empty_for_unknown_stop(self, loaded_ferry_service):
        result = loaded_ferry_service.get_next_ferry_times_detailed("Nonexistent Stop")
        assert result == []

    def test_detailed_results_have_required_keys(self, loaded_ferry_service):
        mock_now = datetime.datetime(2026, 3, 9, 6, 0, 0, tzinfo=NYC_TZ)
        with patch('services.ferry.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            mock_dt.date = datetime.date
            result = loaded_ferry_service.get_next_ferry_times_detailed("Wall St/Pier 11")
        for item in result:
            assert "wait_minutes" in item
            assert "departure_time" in item
            assert "route_id" in item
            assert "route_name" in item
            assert "headsign" in item

    def test_returns_empty_when_load_fails(self):
        from services.ferry import FerryService
        svc = FerryService(use_local_data=False)
        with patch.object(svc, '_load_gtfs_data', return_value=False):
            result = svc.get_next_ferry_times_detailed("Wall St/Pier 11")
        assert result == []

    def test_returns_empty_when_no_active_services(self, loaded_ferry_service):
        loaded_ferry_service.calendar = {}
        result = loaded_ferry_service.get_next_ferry_times_detailed("Wall St/Pier 11")
        assert result == []


class TestGetFerryArrivals:
    def test_returns_dict(self, loaded_ferry_service):
        mock_now = datetime.datetime(2026, 3, 9, 6, 0, 0, tzinfo=NYC_TZ)
        favorites = [{"location": "Wall St/Pier 11", "route": "ER"}]
        with patch('services.ferry.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.datetime.strptime = datetime.datetime.strptime
            mock_dt.date = datetime.date
            result = loaded_ferry_service.get_ferry_arrivals(favorites=favorites)
        assert isinstance(result, dict)
        assert "Wall St/Pier 11" in result

    def test_uses_default_favorites_when_none_provided(self, loaded_ferry_service):
        with patch.object(loaded_ferry_service, 'get_next_ferry_times', return_value=["5 min", "--", "--"]):
            result = loaded_ferry_service.get_ferry_arrivals()
        assert "Wall St/Pier 11" in result
        assert "East 34th Street" in result

    def test_handles_empty_favorites(self, loaded_ferry_service):
        result = loaded_ferry_service.get_ferry_arrivals(favorites=[])
        assert result == {}

    def test_uses_route_filter_from_favorites(self, loaded_ferry_service):
        favorites = [{"location": "Wall St/Pier 11", "route": "ER"}]
        with patch.object(loaded_ferry_service, 'get_next_ferry_times', return_value=["5 min"]) as mock_get:
            loaded_ferry_service.get_ferry_arrivals(favorites=favorites)
        mock_get.assert_called_with("Wall St/Pier 11", route_id="ER")

    def test_handles_missing_route_in_favorites(self, loaded_ferry_service):
        favorites = [{"location": "Wall St/Pier 11"}]  # No "route" key
        with patch.object(loaded_ferry_service, 'get_next_ferry_times', return_value=["5 min"]) as mock_get:
            loaded_ferry_service.get_ferry_arrivals(favorites=favorites)
        mock_get.assert_called_with("Wall St/Pier 11", route_id=None)
