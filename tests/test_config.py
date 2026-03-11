"""Tests for services/config.py"""
import json
import os
import pytest
from unittest.mock import patch, mock_open, MagicMock


class TestDefaultConfig:
    def test_default_station_config_structure(self):
        from services.config import DEFAULT_STATION_CONFIG
        assert "train_favorites" in DEFAULT_STATION_CONFIG
        assert "bus_favorites" in DEFAULT_STATION_CONFIG
        assert "ferry_favorites" in DEFAULT_STATION_CONFIG

    def test_train_favorites_have_required_fields(self):
        from services.config import DEFAULT_STATION_CONFIG
        for fav in DEFAULT_STATION_CONFIG["train_favorites"]:
            assert "station" in fav
            assert "line" in fav
            assert "direction" in fav
            assert "css_class" in fav

    def test_bus_favorites_have_required_fields(self):
        from services.config import DEFAULT_STATION_CONFIG
        for fav in DEFAULT_STATION_CONFIG["bus_favorites"]:
            assert "bus" in fav
            assert "location" in fav
            assert "direction" in fav

    def test_ferry_favorites_have_required_fields(self):
        from services.config import DEFAULT_STATION_CONFIG
        for fav in DEFAULT_STATION_CONFIG["ferry_favorites"]:
            assert "location" in fav

    def test_default_config_not_empty(self):
        from services.config import DEFAULT_STATION_CONFIG
        assert len(DEFAULT_STATION_CONFIG["train_favorites"]) > 0
        assert len(DEFAULT_STATION_CONFIG["bus_favorites"]) > 0
        assert len(DEFAULT_STATION_CONFIG["ferry_favorites"]) > 0


class TestSubwayLines:
    def test_subway_lines_defined(self):
        from services.config import SUBWAY_LINES
        assert len(SUBWAY_LINES) > 0

    def test_subway_lines_have_name_and_css_class(self):
        from services.config import SUBWAY_LINES
        for line_id, info in SUBWAY_LINES.items():
            assert "name" in info
            assert "css_class" in info

    def test_common_subway_lines_present(self):
        from services.config import SUBWAY_LINES
        for line in ["1", "2", "3", "4", "5", "6", "A", "C", "E", "N", "Q", "R", "L", "G"]:
            assert line in SUBWAY_LINES

    def test_express_lines_present(self):
        from services.config import SUBWAY_LINES
        assert "6X" in SUBWAY_LINES
        assert "7X" in SUBWAY_LINES

    def test_css_classes_are_strings(self):
        from services.config import SUBWAY_LINES
        for _, info in SUBWAY_LINES.items():
            assert isinstance(info["css_class"], str)
            assert len(info["css_class"]) > 0


class TestDirections:
    def test_directions_list_not_empty(self):
        from services.config import DIRECTIONS
        assert len(DIRECTIONS) > 0

    def test_uptown_downtown_present(self):
        from services.config import DIRECTIONS
        assert "Uptown" in DIRECTIONS
        assert "Downtown" in DIRECTIONS

    def test_all_directions_are_strings(self):
        from services.config import DIRECTIONS
        for d in DIRECTIONS:
            assert isinstance(d, str)


class TestBusLines:
    def test_common_bus_lines_not_empty(self):
        from services.config import COMMON_BUS_LINES
        assert len(COMMON_BUS_LINES) > 0

    def test_manhattan_bus_lines_present(self):
        from services.config import COMMON_BUS_LINES
        assert "M1" in COMMON_BUS_LINES
        assert "M14A" in COMMON_BUS_LINES

    def test_brooklyn_bus_lines_present(self):
        from services.config import COMMON_BUS_LINES
        assert "B62" in COMMON_BUS_LINES

    def test_queens_bus_lines_present(self):
        from services.config import COMMON_BUS_LINES
        assert "Q18" in COMMON_BUS_LINES

    def test_bronx_bus_lines_present(self):
        from services.config import COMMON_BUS_LINES
        assert "Bx1" in COMMON_BUS_LINES

    def test_bus_directions_not_empty(self):
        from services.config import BUS_DIRECTIONS
        assert len(BUS_DIRECTIONS) > 0

    def test_bus_directions_have_key_directions(self):
        from services.config import BUS_DIRECTIONS
        assert "Northbound" in BUS_DIRECTIONS
        assert "Southbound" in BUS_DIRECTIONS
        assert "Eastbound" in BUS_DIRECTIONS
        assert "Westbound" in BUS_DIRECTIONS


class TestFerryConfig:
    def test_ferry_stops_not_empty(self):
        from services.config import FERRY_STOPS
        assert len(FERRY_STOPS) > 0

    def test_ferry_stops_are_strings(self):
        from services.config import FERRY_STOPS
        for stop in FERRY_STOPS:
            assert isinstance(stop, str)

    def test_ferry_routes_not_empty(self):
        from services.config import FERRY_ROUTES
        assert len(FERRY_ROUTES) > 0

    def test_ferry_routes_have_required_fields(self):
        from services.config import FERRY_ROUTES
        for route in FERRY_ROUTES:
            assert "id" in route
            assert "name" in route
            assert "color" in route

    def test_ferry_routes_colors_are_hex(self):
        from services.config import FERRY_ROUTES
        for route in FERRY_ROUTES:
            assert route["color"].startswith("#")


class TestShuttleTiming:
    def test_shuttle_timing_has_two_locations(self):
        from services.config import SHUTTLE_TIMING
        assert "10 Halletts Point" in SHUTTLE_TIMING
        assert "30th Ave & 31st St" in SHUTTLE_TIMING

    def test_shuttle_times_are_lists(self):
        from services.config import SHUTTLE_TIMING
        for location, times in SHUTTLE_TIMING.items():
            assert isinstance(times, list)
            assert len(times) > 0

    def test_shuttle_times_format(self):
        from services.config import SHUTTLE_TIMING
        import datetime
        for location, times in SHUTTLE_TIMING.items():
            for t in times:
                # Should be parseable as "H:MM AM/PM"
                parsed = datetime.datetime.strptime(t, "%I:%M %p")
                assert parsed is not None

    def test_shuttle_times_sorted(self):
        from services.config import SHUTTLE_TIMING
        import datetime
        for location, times in SHUTTLE_TIMING.items():
            parsed = [datetime.datetime.strptime(t, "%I:%M %p") for t in times]
            assert parsed == sorted(parsed)


class TestLoadStationConfig:
    def test_returns_default_when_no_file(self, tmp_path):
        from services.config import DEFAULT_STATION_CONFIG
        with patch("services.config.CONFIG_FILE", str(tmp_path / "nonexistent.json")):
            from services.config import load_station_config
            result = load_station_config()
        assert result == DEFAULT_STATION_CONFIG

    def test_loads_from_file_when_exists(self, tmp_path):
        config_file = tmp_path / "station_config.json"
        custom_config = {"train_favorites": [], "bus_favorites": [], "ferry_favorites": []}
        config_file.write_text(json.dumps(custom_config))
        with patch("services.config.CONFIG_FILE", str(config_file)):
            from services.config import load_station_config
            result = load_station_config()
        assert result == custom_config

    def test_returns_default_on_invalid_json(self, tmp_path):
        from services.config import DEFAULT_STATION_CONFIG
        config_file = tmp_path / "station_config.json"
        config_file.write_text("not valid json{{{")
        with patch("services.config.CONFIG_FILE", str(config_file)):
            from services.config import load_station_config
            result = load_station_config()
        assert result == DEFAULT_STATION_CONFIG

    def test_returns_default_on_empty_file(self, tmp_path):
        from services.config import DEFAULT_STATION_CONFIG
        config_file = tmp_path / "station_config.json"
        config_file.write_text("")
        with patch("services.config.CONFIG_FILE", str(config_file)):
            from services.config import load_station_config
            result = load_station_config()
        assert result == DEFAULT_STATION_CONFIG


class TestSaveStationConfig:
    def test_saves_config_to_file(self, tmp_path):
        config_file = tmp_path / "station_config.json"
        config = {"train_favorites": [{"station": "Test"}], "bus_favorites": []}
        with patch("services.config.CONFIG_FILE", str(config_file)):
            from services.config import save_station_config
            save_station_config(config)
        saved = json.loads(config_file.read_text())
        assert saved == config

    def test_saved_config_is_valid_json(self, tmp_path):
        config_file = tmp_path / "station_config.json"
        config = {"key": "value", "nested": {"a": 1}}
        with patch("services.config.CONFIG_FILE", str(config_file)):
            from services.config import save_station_config
            save_station_config(config)
        content = config_file.read_text()
        parsed = json.loads(content)
        assert parsed == config

    def test_save_overwrites_existing(self, tmp_path):
        config_file = tmp_path / "station_config.json"
        config_file.write_text(json.dumps({"old": "data"}))
        new_config = {"new": "data"}
        with patch("services.config.CONFIG_FILE", str(config_file)):
            from services.config import save_station_config
            save_station_config(new_config)
        saved = json.loads(config_file.read_text())
        assert saved == new_config


class TestLoadStationsList:
    def test_returns_list(self):
        from services.config import load_stations_list
        result = load_stations_list()
        assert isinstance(result, list)

    def test_falls_back_to_hardcoded(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from services.config import load_stations_list
        # No CSV or JSON file exists in tmp_path
        result = load_stations_list()
        assert len(result) >= 3
        assert "Union Square - 14th St" in result

    def test_loads_from_json_if_csv_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        stations_data = {"subway_stations": ["Station A", "Station B", "Station C"]}
        (tmp_path / "stations.json").write_text(json.dumps(stations_data))
        from services.config import load_stations_list
        result = load_stations_list()
        assert "Station A" in result
        assert "Station B" in result

    def test_loads_from_csv_when_available(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        csv_content = "Stop Name,Other Col\nGrand Central,1\nTimes Sq,2\n"
        (tmp_path / "Stations.csv").write_text(csv_content)
        from services.config import load_stations_list
        result = load_stations_list()
        assert "Grand Central" in result
        assert "Times Sq" in result
