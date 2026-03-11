"""Tests for services/alerts.py"""
import pytest
from unittest.mock import patch, MagicMock


class TestAlertsServiceUrl:
    def test_mta_alerts_url_defined(self):
        from services.alerts import MTA_ALERTS_URL
        assert MTA_ALERTS_URL is not None
        assert "mta" in MTA_ALERTS_URL.lower()
        assert MTA_ALERTS_URL.startswith("https://")


class TestGetServiceAlerts:
    def test_returns_empty_list_on_network_error(self):
        from services.alerts import AlertsService
        svc = AlertsService()
        with patch('requests.get', side_effect=Exception("network error")):
            result = svc.get_service_alerts()
        assert result == []

    def test_returns_empty_list_on_http_error(self):
        from services.alerts import AlertsService
        svc = AlertsService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()
        assert result == []

    def test_returns_empty_list_on_parse_error(self):
        from services.alerts import AlertsService
        svc = AlertsService()
        mock_resp = MagicMock()
        mock_resp.content = b"invalid protobuf data"
        with patch('requests.get', return_value=mock_resp):
            from google.transit import gtfs_realtime_pb2
            with patch.object(gtfs_realtime_pb2.FeedMessage, 'ParseFromString', side_effect=Exception("parse error")):
                result = svc.get_service_alerts()
        assert result == []

    def test_returns_list_type(self):
        from services.alerts import AlertsService
        svc = AlertsService()
        with patch('requests.get', side_effect=Exception("network error")):
            result = svc.get_service_alerts()
        assert isinstance(result, list)

    def test_parses_alert_from_feed(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        # Create a real protobuf FeedMessage with an alert
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        entity = feed.entity.add()
        entity.id = "1"
        alert = entity.alert

        # Set header text
        translation = alert.header_text.translation.add()
        translation.text = "Test Alert Header"
        translation.language = "en"

        # Set description text
        desc_translation = alert.description_text.translation.add()
        desc_translation.text = "Test Alert Description"
        desc_translation.language = "en"

        # Set informed entity
        informed = alert.informed_entity.add()
        informed.route_id = "4"

        serialized = feed.SerializeToString()

        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()

        assert len(result) == 1
        assert result[0]["header"] == "Test Alert Header"
        assert result[0]["description"] == "Test Alert Description"
        assert "4" in result[0]["routes"]

    def test_filters_by_routes(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        # Alert for route 4
        entity1 = feed.entity.add()
        entity1.id = "1"
        alert1 = entity1.alert
        translation1 = alert1.header_text.translation.add()
        translation1.text = "Route 4 Alert"
        informed1 = alert1.informed_entity.add()
        informed1.route_id = "4"

        # Alert for route N
        entity2 = feed.entity.add()
        entity2.id = "2"
        alert2 = entity2.alert
        translation2 = alert2.header_text.translation.add()
        translation2.text = "Route N Alert"
        informed2 = alert2.informed_entity.add()
        informed2.route_id = "N"

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts(routes=["4"])

        assert len(result) == 1
        assert result[0]["header"] == "Route 4 Alert"

    def test_no_route_filter_returns_all_alerts(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        for i in range(2):
            entity = feed.entity.add()
            entity.id = str(i)
            alert = entity.alert
            translation = alert.header_text.translation.add()
            translation.text = f"Alert {i}"
            informed = alert.informed_entity.add()
            informed.route_id = str(i + 1)

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()  # No routes filter

        assert len(result) == 2

    def test_limits_to_three_alerts(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        # Create 5 alerts
        for i in range(5):
            entity = feed.entity.add()
            entity.id = str(i)
            alert = entity.alert
            translation = alert.header_text.translation.add()
            translation.text = f"Alert {i}"
            informed = alert.informed_entity.add()
            informed.route_id = str(i + 1)

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()

        assert len(result) <= 3

    def test_alert_dict_has_required_keys(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        entity = feed.entity.add()
        entity.id = "1"
        alert = entity.alert
        translation = alert.header_text.translation.add()
        translation.text = "Test Alert"
        informed = alert.informed_entity.add()
        informed.route_id = "L"

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()

        assert len(result) == 1
        alert_dict = result[0]
        assert "header" in alert_dict
        assert "description" in alert_dict
        assert "effect" in alert_dict
        assert "routes" in alert_dict

    def test_alert_routes_is_list(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        entity = feed.entity.add()
        entity.id = "1"
        alert = entity.alert
        translation = alert.header_text.translation.add()
        translation.text = "Multi-route Alert"
        for route in ["A", "C", "E"]:
            informed = alert.informed_entity.add()
            informed.route_id = route

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()

        assert len(result) == 1
        assert isinstance(result[0]["routes"], list)
        assert "A" in result[0]["routes"]
        assert "C" in result[0]["routes"]
        assert "E" in result[0]["routes"]

    def test_skips_non_alert_entities(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        # Add a trip update entity (not an alert)
        entity1 = feed.entity.add()
        entity1.id = "1"
        tu = entity1.trip_update
        tu.trip.route_id = "4"

        # Add an alert entity
        entity2 = feed.entity.add()
        entity2.id = "2"
        alert = entity2.alert
        translation = alert.header_text.translation.add()
        translation.text = "Real Alert"
        informed = alert.informed_entity.add()
        informed.route_id = "6"

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()

        # Only the alert entity should be in results
        assert len(result) == 1
        assert result[0]["header"] == "Real Alert"

    def test_handles_alert_with_empty_header(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        entity = feed.entity.add()
        entity.id = "1"
        alert = entity.alert
        # No header text translations
        informed = alert.informed_entity.add()
        informed.route_id = "7"

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()

        assert len(result) == 1
        assert result[0]["header"] == ""

    def test_returns_empty_list_when_no_matching_routes(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        entity = feed.entity.add()
        entity.id = "1"
        alert = entity.alert
        translation = alert.header_text.translation.add()
        translation.text = "Route 4 Alert"
        informed = alert.informed_entity.add()
        informed.route_id = "4"

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts(routes=["N", "Q"])  # No overlap

        assert result == []

    def test_accepts_multiple_route_filter(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        # Alert for route N
        entity1 = feed.entity.add()
        entity1.id = "1"
        alert1 = entity1.alert
        t1 = alert1.header_text.translation.add()
        t1.text = "N Alert"
        i1 = alert1.informed_entity.add()
        i1.route_id = "N"

        # Alert for route Q
        entity2 = feed.entity.add()
        entity2.id = "2"
        alert2 = entity2.alert
        t2 = alert2.header_text.translation.add()
        t2.text = "Q Alert"
        i2 = alert2.informed_entity.add()
        i2.route_id = "Q"

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts(routes=["N", "Q"])

        assert len(result) == 2

    def test_effect_field_is_string(self):
        from services.alerts import AlertsService
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1700000000

        entity = feed.entity.add()
        entity.id = "1"
        alert = entity.alert
        translation = alert.header_text.translation.add()
        translation.text = "Reduced Service"
        alert.effect = gtfs_realtime_pb2.Alert.Effect.Value("REDUCED_SERVICE")
        informed = alert.informed_entity.add()
        informed.route_id = "L"

        serialized = feed.SerializeToString()
        mock_resp = MagicMock()
        mock_resp.content = serialized

        svc = AlertsService()
        with patch('requests.get', return_value=mock_resp):
            result = svc.get_service_alerts()

        assert isinstance(result[0]["effect"], str)
