import requests
import streamlit as st
from typing import List, Optional

MTA_ALERTS_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fall-alerts"


class AlertsService:
    def get_service_alerts(self, routes: Optional[List[str]] = None) -> List[dict]:
        """
        Fetch active MTA service alerts, optionally filtered to specific route IDs.

        Returns up to 3 alerts as dicts with keys:
            header, description, effect, routes
        Returns [] on missing API key, network error, or parse failure.
        """
        api_key = st.secrets.get("mta_api_key", "")
        if not api_key or api_key == "YOUR_MTA_API_KEY":
            return []

        try:
            from google.transit import gtfs_realtime_pb2
        except ImportError:
            return []

        try:
            response = requests.get(
                MTA_ALERTS_URL,
                headers={"x-api-key": api_key},
                timeout=5,
            )
            response.raise_for_status()
        except Exception:
            return []

        try:
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
        except Exception:
            return []

        alerts = []
        for entity in feed.entity:
            if not entity.HasField("alert"):
                continue
            alert = entity.alert

            # Collect route IDs this alert affects
            affected_routes = []
            for informed in alert.informed_entity:
                if informed.route_id:
                    affected_routes.append(informed.route_id)

            # Filter: skip alerts that don't touch any of the requested routes
            if routes:
                if not any(r in routes for r in affected_routes):
                    continue

            header = ""
            if alert.header_text.translation:
                header = alert.header_text.translation[0].text

            description = ""
            if alert.description_text.translation:
                description = alert.description_text.translation[0].text

            effect = alert.Effect.Name(alert.effect) if alert.effect else ""

            alerts.append({
                "header": header,
                "description": description,
                "effect": effect,
                "routes": affected_routes,
            })

            if len(alerts) >= 3:
                break

        return alerts
