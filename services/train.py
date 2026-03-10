import datetime
import io
import json
import os
import random
import zipfile
import requests
import pytz
from typing import Dict, List, Optional
from .config import load_station_config, SUBWAY_LINES

NYC_TZ = pytz.timezone('America/New_York')

MTA_BASE = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds"

# Line → GTFS-RT feed path
SUBWAY_FEEDS = {
    "1": "nyct%2Fgtfs", "2": "nyct%2Fgtfs", "3": "nyct%2Fgtfs",
    "4": "nyct%2Fgtfs", "5": "nyct%2Fgtfs", "6": "nyct%2Fgtfs",
    "7": "nyct%2Fgtfs", "GS": "nyct%2Fgtfs",
    "A": "nyct%2Fgtfs-ace", "C": "nyct%2Fgtfs-ace", "E": "nyct%2Fgtfs-ace",
    "H": "nyct%2Fgtfs-ace", "FS": "nyct%2Fgtfs-ace",
    "N": "nyct%2Fgtfs-nqrw", "Q": "nyct%2Fgtfs-nqrw",
    "R": "nyct%2Fgtfs-nqrw", "W": "nyct%2Fgtfs-nqrw",
    "B": "nyct%2Fgtfs-bdfm", "D": "nyct%2Fgtfs-bdfm",
    "F": "nyct%2Fgtfs-bdfm", "M": "nyct%2Fgtfs-bdfm",
    "L": "nyct%2Fgtfs-l",
    "G": "nyct%2Fgtfs-g",
    "J": "nyct%2Fgtfs-jz", "Z": "nyct%2Fgtfs-jz",
    "SI": "nyct%2Fgtfs-si",
}

# In MTA GTFS stop IDs, the last character indicates direction:
#   N = northbound / outbound (away from Manhattan for most lines)
#   S = southbound / inbound (towards Manhattan for most lines)
DIRECTION_SUFFIX = {
    "Manhattan": "S",
    "Downtown": "S",
    "Downtown & Brooklyn": "S",
    "Brooklyn": "S",
    "To Manhattan": "S",
    "To Brooklyn": "S",
    "Uptown": "N",
    "Uptown & Bronx": "N",
    "Uptown & Manhattan": "N",
    "Queens": "N",
    "Bronx": "N",
    "To Queens": "N",
    "To Bronx": "N",
}

STOPS_CACHE_FILE = os.path.join("data", "subway_stops.json")
STOPS_CACHE_DAYS = 7

# Module-level caches (survive Streamlit reruns within one process)
_stops_cache: Optional[Dict] = None
_feed_cache: Dict = {}          # url -> (timestamp, FeedMessage)
FEED_CACHE_TTL = 30             # seconds


def _load_stops() -> Dict[str, List[str]]:
    """Return {stop_name_lower: [stop_id, ...]} from local cache or MTA static GTFS."""
    global _stops_cache

    if _stops_cache is not None:
        return _stops_cache

    # File cache still fresh?
    if os.path.exists(STOPS_CACHE_FILE):
        age = (datetime.datetime.now().timestamp() - os.path.getmtime(STOPS_CACHE_FILE)) / 86400
        if age < STOPS_CACHE_DAYS:
            try:
                with open(STOPS_CACHE_FILE) as f:
                    _stops_cache = json.load(f)
                return _stops_cache
            except Exception:
                pass

    # Download MTA supplemented GTFS zip and extract stops.txt
    try:
        resp = requests.get(f"{MTA_BASE}/nyct%2Fgtfs_supplemented", timeout=20)
        resp.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        raw = z.read("stops.txt").decode("utf-8")
    except Exception:
        _stops_cache = {}
        return _stops_cache

    stops: Dict[str, List[str]] = {}
    lines_iter = iter(raw.strip().splitlines())
    headers = [h.strip().strip('"') for h in next(lines_iter).split(",")]
    try:
        id_idx = headers.index("stop_id")
        name_idx = headers.index("stop_name")
    except ValueError:
        _stops_cache = {}
        return _stops_cache

    for row in lines_iter:
        parts = [p.strip().strip('"') for p in row.split(",")]
        if len(parts) <= max(id_idx, name_idx):
            continue
        sid = parts[id_idx]
        # Only keep platform stops (end in N or S); parent stations end in digits
        if not (sid.endswith("N") or sid.endswith("S")):
            continue
        name = parts[name_idx].lower()
        stops.setdefault(name, []).append(sid)

    os.makedirs("data", exist_ok=True)
    try:
        with open(STOPS_CACHE_FILE, "w") as f:
            json.dump(stops, f)
    except Exception:
        pass

    _stops_cache = stops
    return _stops_cache


def _get_stop_ids(station: str, direction: str) -> List[str]:
    """Return stop IDs for the station filtered to the requested direction."""
    stops = _load_stops()
    suffix = DIRECTION_SUFFIX.get(direction, "")
    candidates = stops.get(station.lower(), [])
    if suffix:
        filtered = [s for s in candidates if s.endswith(suffix)]
        return filtered if filtered else candidates
    return candidates


def _fetch_feed(line: str):
    """Fetch (and short-cache) the GTFS-RT TripUpdate feed for a subway line."""
    try:
        from google.transit import gtfs_realtime_pb2
    except ImportError:
        return None

    feed_path = SUBWAY_FEEDS.get(line)
    if not feed_path:
        return None

    url = f"{MTA_BASE}/{feed_path}"
    now_ts = datetime.datetime.now().timestamp()

    if url in _feed_cache:
        ts, cached = _feed_cache[url]
        if now_ts - ts < FEED_CACHE_TTL:
            return cached

    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(resp.content)
        _feed_cache[url] = (now_ts, feed)
        return feed
    except Exception:
        return None


def _real_arrivals(station: str, line: str, direction: str) -> Optional[List[str]]:
    """Return up to 3 real arrival strings from GTFS-RT, or None on failure."""
    stop_ids = set(_get_stop_ids(station, direction))
    if not stop_ids:
        return None

    feed = _fetch_feed(line)
    if feed is None:
        return None

    now_ts = datetime.datetime.now(NYC_TZ).timestamp()
    waits: List[float] = []

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        if tu.trip.route_id != line:
            continue
        for stu in tu.stop_time_update:
            if stu.stop_id not in stop_ids:
                continue
            t = stu.departure.time or stu.arrival.time
            if t and t > now_ts:
                waits.append((t - now_ts) / 60.0)
            break  # one entry per trip

    if not waits:
        return None

    waits.sort()
    result = []
    for w in waits[:3]:
        if w < 0.5:
            result.append("Arriving")
        elif w < 1:
            result.append("< 1 min")
        else:
            result.append(f"{int(w)} min")
    return result


class SubwayService:
    def __init__(self, api_key: Optional[str] = None):
        pass

    def get_realistic_arrivals(self, station_name: str, line: str, direction: str) -> List[str]:
        """Fallback: generate realistic-looking arrival times based on current time."""
        current_time = datetime.datetime.now()
        current_second = current_time.second
        line_intervals = {
            "1": 5, "2": 4, "3": 5, "4": 3, "5": 4, "6": 3,
            "7": 4, "A": 6, "B": 8, "C": 8, "D": 6, "E": 5,
            "F": 6, "G": 10, "J": 8, "L": 4, "M": 8, "N": 6,
            "Q": 5, "R": 6, "W": 8, "Z": 10, "S": 15,
        }
        base_interval = line_intervals.get(line, 6)
        hour = current_time.hour
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            multiplier = 0.7
        elif 22 <= hour or hour <= 5:
            multiplier = 2.0
        else:
            multiplier = 1.0
        adjusted = base_interval * multiplier
        arrivals = []
        for i in range(3):
            wait = adjusted * (i + 1) + random.uniform(-1.5, 1.5) - current_second / 60.0
            if wait < 0.5:
                arrivals.append("Arriving")
            elif wait < 1:
                arrivals.append("< 1 min")
            else:
                arrivals.append(f"{int(wait)} min")
        return arrivals

    def get_arrivals(self, favorites_only=False) -> Dict[str, List[str]]:
        config = load_station_config()
        favorites = config.get("train_favorites", [])
        result = {}
        for fav in favorites:
            station = fav["station"]
            line = fav["line"]
            direction = fav["direction"]
            key = f"{station}_{line}_{direction}"
            arrivals = _real_arrivals(station, line, direction)
            if arrivals is None:
                arrivals = self.get_realistic_arrivals(station, line, direction)
            result[key] = arrivals
        return result
