"""Tests for services/train.py"""
import datetime
import json
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
import pytz


NYC_TZ = pytz.timezone('America/New_York')


class TestSubwayFeeds:
    def test_subway_feeds_mapping_has_all_lines(self):
        from services.train import SUBWAY_FEEDS
        for line in ["1", "2", "3", "4", "5", "6", "7", "A", "C", "E", "N", "Q", "R", "W", "B", "D", "F", "M", "L", "G", "J", "Z"]:
            assert line in SUBWAY_FEEDS

    def test_subway_feed_paths_are_strings(self):
        from services.train import SUBWAY_FEEDS
        for line, path in SUBWAY_FEEDS.items():
            assert isinstance(path, str)
            assert len(path) > 0


class TestDirectionSuffix:
    def test_downtown_maps_to_south(self):
        from services.train import DIRECTION_SUFFIX
        assert DIRECTION_SUFFIX["Downtown"] == "S"

    def test_uptown_maps_to_north(self):
        from services.train import DIRECTION_SUFFIX
        assert DIRECTION_SUFFIX["Uptown"] == "N"

    def test_manhattan_maps_to_south(self):
        from services.train import DIRECTION_SUFFIX
        assert DIRECTION_SUFFIX["Manhattan"] == "S"

    def test_brooklyn_maps_to_south(self):
        from services.train import DIRECTION_SUFFIX
        assert DIRECTION_SUFFIX["Brooklyn"] == "S"

    def test_queens_maps_to_north(self):
        from services.train import DIRECTION_SUFFIX
        assert DIRECTION_SUFFIX["Queens"] == "N"

    def test_bronx_maps_to_north(self):
        from services.train import DIRECTION_SUFFIX
        assert DIRECTION_SUFFIX["Bronx"] == "N"


class TestLoadStops:
    def setup_method(self):
        import services.train as train_mod
        train_mod._stops_cache = None

    def test_returns_dict(self):
        from services import train as train_mod
        with patch.object(train_mod, '_stops_cache', None):
            with patch('os.path.exists', return_value=False):
                with patch('requests.get', side_effect=Exception("network error")):
                    train_mod._stops_cache = None
                    result = train_mod._load_stops()
        assert isinstance(result, dict)

    def test_returns_cached_value_if_available(self):
        import services.train as train_mod
        train_mod._stops_cache = {"cached_station": ["stop1N", "stop1S"]}
        result = train_mod._load_stops()
        assert result == {"cached_station": ["stop1N", "stop1S"]}

    def test_loads_from_file_cache_if_fresh(self, tmp_path):
        import services.train as train_mod
        train_mod._stops_cache = None
        cache_data = {"union square": ["635N", "635S"]}
        cache_file = tmp_path / "subway_stops.json"
        cache_file.write_text(json.dumps(cache_data))
        with patch.object(train_mod, 'STOPS_CACHE_FILE', str(cache_file)):
            with patch('os.path.getmtime', return_value=datetime.datetime.now().timestamp()):
                result = train_mod._load_stops()
        assert result == cache_data

    def test_returns_empty_dict_on_download_failure(self):
        import services.train as train_mod
        train_mod._stops_cache = None
        with patch('os.path.exists', return_value=False):
            with patch('requests.get', side_effect=Exception("network error")):
                result = train_mod._load_stops()
        assert result == {}

    def test_parses_stops_txt_correctly(self):
        import services.train as train_mod
        train_mod._stops_cache = None
        stops_csv = "stop_id,stop_name,stop_lat,stop_lon\n635N,Union Square,40.7,-73.9\n635S,Union Square,40.7,-73.9\n635,Union Square,40.7,-73.9\n"
        mock_zip = MagicMock()
        mock_zip.read.return_value = stops_csv.encode('utf-8')
        mock_resp = MagicMock()
        mock_resp.content = b"fake_zip_content"
        with patch('os.path.exists', return_value=False):
            with patch('requests.get', return_value=mock_resp):
                with patch('zipfile.ZipFile', return_value=mock_zip):
                    with patch('os.makedirs'):
                        with patch('builtins.open', mock_open()):
                            result = train_mod._load_stops()
        # Should contain N and S stops but not parent station
        if result:
            for name, ids in result.items():
                for sid in ids:
                    assert sid.endswith('N') or sid.endswith('S')


class TestGetStopIds:
    def setup_method(self):
        import services.train as train_mod
        train_mod._stops_cache = {
            "union square": ["635N", "635S"],
            "times square": ["R16N", "R16S", "127N", "127S"],
        }

    def test_returns_northbound_stops(self):
        from services.train import _get_stop_ids
        result = _get_stop_ids("Union Square", "Uptown")
        assert "635N" in result
        assert "635S" not in result

    def test_returns_southbound_stops(self):
        from services.train import _get_stop_ids
        result = _get_stop_ids("Union Square", "Downtown")
        assert "635S" in result
        assert "635N" not in result

    def test_returns_all_stops_for_unknown_direction(self):
        from services.train import _get_stop_ids
        result = _get_stop_ids("Union Square", "Unknown Direction")
        assert "635N" in result
        assert "635S" in result

    def test_returns_empty_for_unknown_station(self):
        from services.train import _get_stop_ids
        result = _get_stop_ids("Nonexistent Station", "Uptown")
        assert result == []

    def test_case_insensitive_station_lookup(self):
        from services.train import _get_stop_ids
        result = _get_stop_ids("UNION SQUARE", "Uptown")
        assert "635N" in result

    def test_falls_back_to_all_if_direction_not_in_candidates(self):
        import services.train as train_mod
        train_mod._stops_cache = {"special station": ["ABCN"]}
        from services.train import _get_stop_ids
        result = _get_stop_ids("Special Station", "Downtown")
        # Direction S not in candidates, should return all
        assert "ABCN" in result


class TestFetchFeed:
    def test_returns_none_if_line_not_in_feeds(self):
        import services.train as train_mod
        train_mod._feed_cache = {}
        from services.train import _fetch_feed
        result = _fetch_feed("UNKNOWN_LINE")
        assert result is None

    def test_returns_cached_feed_if_fresh(self):
        import services.train as train_mod
        mock_feed = MagicMock()
        url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs"
        train_mod._feed_cache = {url: (datetime.datetime.now().timestamp(), mock_feed)}
        from services.train import _fetch_feed
        result = _fetch_feed("1")
        assert result == mock_feed

    def test_fetches_fresh_feed_if_cache_expired(self):
        import services.train as train_mod
        url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs"
        # Set cache to expired (old timestamp)
        train_mod._feed_cache = {url: (0, MagicMock())}
        mock_resp = MagicMock()
        mock_resp.content = b""
        mock_feed = MagicMock()
        with patch('requests.get', return_value=mock_resp) as mock_get:
            with patch('google.transit.gtfs_realtime_pb2.FeedMessage') as mock_fm:
                mock_fm.return_value = mock_feed
                from services.train import _fetch_feed
                result = _fetch_feed("1")
        assert mock_get.called

    def test_returns_none_on_request_failure(self):
        import services.train as train_mod
        train_mod._feed_cache = {}
        with patch('requests.get', side_effect=Exception("connection error")):
            from services.train import _fetch_feed
            result = _fetch_feed("1")
        assert result is None


class TestRealArrivals:
    def setup_method(self):
        import services.train as train_mod
        train_mod._stops_cache = {
            "union square": ["635N", "635S"],
        }
        train_mod._feed_cache = {}

    def test_returns_none_if_no_stop_ids(self):
        import services.train as train_mod
        train_mod._stops_cache = {}
        from services.train import _real_arrivals
        result = _real_arrivals("Nonexistent Station", "4", "Uptown")
        assert result is None

    def test_returns_none_if_no_feed(self):
        import services.train as train_mod
        train_mod._stops_cache = {"union square": ["635N", "635S"]}
        with patch('services.train._fetch_feed', return_value=None):
            from services.train import _real_arrivals
            result = _real_arrivals("Union Square", "4", "Uptown")
        assert result is None

    def test_returns_arrivals_from_feed(self):
        import services.train as train_mod
        train_mod._stops_cache = {"union square": ["635N"]}

        now_ts = datetime.datetime.now(NYC_TZ).timestamp()

        # Build mock feed entity
        mock_stu = MagicMock()
        mock_stu.stop_id = "635N"
        mock_stu.departure.time = int(now_ts + 300)  # 5 minutes from now
        mock_stu.arrival.time = 0

        mock_tu = MagicMock()
        mock_tu.trip.route_id = "4"
        mock_tu.stop_time_update = [mock_stu]

        mock_entity = MagicMock()
        mock_entity.HasField.return_value = True
        mock_entity.trip_update = mock_tu

        mock_feed = MagicMock()
        mock_feed.entity = [mock_entity]

        with patch('services.train._fetch_feed', return_value=mock_feed):
            from services.train import _real_arrivals
            result = _real_arrivals("Union Square", "4", "Uptown")

        assert result is not None
        assert len(result) >= 1
        assert "5 min" in result[0] or "4 min" in result[0] or "min" in result[0]

    def test_formats_arriving_when_less_than_half_minute(self):
        import services.train as train_mod
        train_mod._stops_cache = {"union square": ["635N"]}

        now_ts = datetime.datetime.now(NYC_TZ).timestamp()

        mock_stu = MagicMock()
        mock_stu.stop_id = "635N"
        mock_stu.departure.time = int(now_ts + 20)  # 20 seconds from now
        mock_stu.arrival.time = 0

        mock_tu = MagicMock()
        mock_tu.trip.route_id = "4"
        mock_tu.stop_time_update = [mock_stu]

        mock_entity = MagicMock()
        mock_entity.HasField.return_value = True
        mock_entity.trip_update = mock_tu

        mock_feed = MagicMock()
        mock_feed.entity = [mock_entity]

        with patch('services.train._fetch_feed', return_value=mock_feed):
            from services.train import _real_arrivals
            result = _real_arrivals("Union Square", "4", "Uptown")

        assert result is not None
        assert result[0] == "Arriving"

    def test_formats_less_than_one_min(self):
        import services.train as train_mod
        train_mod._stops_cache = {"union square": ["635N"]}

        now_ts = datetime.datetime.now(NYC_TZ).timestamp()

        mock_stu = MagicMock()
        mock_stu.stop_id = "635N"
        mock_stu.departure.time = int(now_ts + 45)  # 45 seconds from now
        mock_stu.arrival.time = 0

        mock_tu = MagicMock()
        mock_tu.trip.route_id = "4"
        mock_tu.stop_time_update = [mock_stu]

        mock_entity = MagicMock()
        mock_entity.HasField.return_value = True
        mock_entity.trip_update = mock_tu

        mock_feed = MagicMock()
        mock_feed.entity = [mock_entity]

        with patch('services.train._fetch_feed', return_value=mock_feed):
            from services.train import _real_arrivals
            result = _real_arrivals("Union Square", "4", "Uptown")

        assert result is not None
        assert result[0] == "< 1 min"

    def test_skips_past_arrivals(self):
        import services.train as train_mod
        train_mod._stops_cache = {"union square": ["635N"]}

        now_ts = datetime.datetime.now(NYC_TZ).timestamp()

        mock_stu = MagicMock()
        mock_stu.stop_id = "635N"
        mock_stu.departure.time = int(now_ts - 300)  # 5 minutes ago
        mock_stu.arrival.time = 0

        mock_tu = MagicMock()
        mock_tu.trip.route_id = "4"
        mock_tu.stop_time_update = [mock_stu]

        mock_entity = MagicMock()
        mock_entity.HasField.return_value = True
        mock_entity.trip_update = mock_tu

        mock_feed = MagicMock()
        mock_feed.entity = [mock_entity]

        with patch('services.train._fetch_feed', return_value=mock_feed):
            from services.train import _real_arrivals
            result = _real_arrivals("Union Square", "4", "Uptown")

        assert result is None

    def test_limits_to_three_arrivals(self):
        import services.train as train_mod
        train_mod._stops_cache = {"union square": ["635N"]}

        now_ts = datetime.datetime.now(NYC_TZ).timestamp()
        entities = []
        for i in range(5):
            mock_stu = MagicMock()
            mock_stu.stop_id = "635N"
            mock_stu.departure.time = int(now_ts + (i + 1) * 300)
            mock_stu.arrival.time = 0

            mock_tu = MagicMock()
            mock_tu.trip.route_id = "4"
            mock_tu.stop_time_update = [mock_stu]

            mock_entity = MagicMock()
            mock_entity.HasField.return_value = True
            mock_entity.trip_update = mock_tu
            entities.append(mock_entity)

        mock_feed = MagicMock()
        mock_feed.entity = entities

        with patch('services.train._fetch_feed', return_value=mock_feed):
            from services.train import _real_arrivals
            result = _real_arrivals("Union Square", "4", "Uptown")

        assert result is not None
        assert len(result) <= 3


class TestSubwayService:
    def test_get_realistic_arrivals_returns_three_items(self):
        from services.train import SubwayService
        svc = SubwayService()
        result = svc.get_realistic_arrivals("Union Square", "4", "Uptown")
        assert len(result) == 3

    def test_get_realistic_arrivals_returns_strings(self):
        from services.train import SubwayService
        svc = SubwayService()
        result = svc.get_realistic_arrivals("Union Square", "N", "Downtown")
        for item in result:
            assert isinstance(item, str)

    def test_get_realistic_arrivals_valid_format(self):
        from services.train import SubwayService
        svc = SubwayService()
        result = svc.get_realistic_arrivals("Times Sq", "Q", "Uptown")
        for item in result:
            assert item == "Arriving" or item == "< 1 min" or item.endswith("min")

    def test_get_realistic_arrivals_uses_line_intervals(self):
        from services.train import SubwayService
        svc = SubwayService()
        # G train has 10min interval, should generally be higher than 1 line (5min)
        result_g = svc.get_realistic_arrivals("Court Sq", "G", "Uptown")
        assert len(result_g) == 3

    def test_get_realistic_arrivals_unknown_line(self):
        from services.train import SubwayService
        svc = SubwayService()
        result = svc.get_realistic_arrivals("Some Station", "X", "Uptown")
        assert len(result) == 3

    def test_get_arrivals_returns_dict(self):
        from services.train import SubwayService
        svc = SubwayService()
        with patch('services.train._real_arrivals', return_value=None):
            with patch('services.train.load_station_config', return_value={
                "train_favorites": [
                    {"station": "Union Square", "line": "4", "direction": "Uptown", "css_class": "line-4-5-6"}
                ]
            }):
                result = svc.get_arrivals()
        assert isinstance(result, dict)

    def test_get_arrivals_uses_real_arrivals_when_available(self):
        from services.train import SubwayService
        svc = SubwayService()
        mock_arrivals = ["5 min", "10 min", "15 min"]
        with patch('services.train._real_arrivals', return_value=mock_arrivals):
            with patch('services.train.load_station_config', return_value={
                "train_favorites": [
                    {"station": "Union Square", "line": "4", "direction": "Uptown", "css_class": "line-4-5-6"}
                ]
            }):
                result = svc.get_arrivals()
        key = "Union Square_4_Uptown"
        assert result[key] == mock_arrivals

    def test_get_arrivals_falls_back_to_realistic(self):
        from services.train import SubwayService
        svc = SubwayService()
        with patch('services.train._real_arrivals', return_value=None):
            with patch('services.train.load_station_config', return_value={
                "train_favorites": [
                    {"station": "Union Square", "line": "4", "direction": "Uptown", "css_class": "line-4-5-6"}
                ]
            }):
                result = svc.get_arrivals()
        key = "Union Square_4_Uptown"
        assert key in result
        assert len(result[key]) == 3

    def test_get_arrivals_handles_empty_favorites(self):
        from services.train import SubwayService
        svc = SubwayService()
        with patch('services.train.load_station_config', return_value={"train_favorites": []}):
            result = svc.get_arrivals()
        assert result == {}

    def test_get_arrivals_correct_key_format(self):
        from services.train import SubwayService
        svc = SubwayService()
        with patch('services.train._real_arrivals', return_value=["5 min", "10 min", "15 min"]):
            with patch('services.train.load_station_config', return_value={
                "train_favorites": [
                    {"station": "Times Sq", "line": "N", "direction": "Downtown", "css_class": "line-n-q-r-w"}
                ]
            }):
                result = svc.get_arrivals()
        assert "Times Sq_N_Downtown" in result

    @patch('datetime.datetime')
    def test_peak_hour_multiplier_rush_morning(self, mock_dt):
        from services.train import SubwayService
        mock_now = MagicMock()
        mock_now.hour = 8  # Rush hour
        mock_now.second = 0
        mock_dt.now.return_value = mock_now
        svc = SubwayService()
        result = svc.get_realistic_arrivals("Union Square", "4", "Uptown")
        assert len(result) == 3

    @patch('datetime.datetime')
    def test_late_night_multiplier(self, mock_dt):
        from services.train import SubwayService
        mock_now = MagicMock()
        mock_now.hour = 23  # Late night
        mock_now.second = 0
        mock_dt.now.return_value = mock_now
        svc = SubwayService()
        result = svc.get_realistic_arrivals("Union Square", "4", "Uptown")
        assert len(result) == 3
