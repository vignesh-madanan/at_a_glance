import datetime
import csv
import os
import io
import zipfile
from typing import Dict, List, Optional
import requests

# NYC Ferry GTFS API endpoints
GTFS_URL = "https://nycferry.connexionz.net/rtt/public/utility/gtfs.aspx"
GTFS_RT_TRIP_UPDATE_URL = "https://nycferry.connexionz.net/rtt/public/utility/gtfsrealtime.aspx/tripupdate"

# Local GTFS data path
LOCAL_GTFS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gtfs")

# Ferry routes with their colors for display
FERRY_ROUTES = {
    "AS": {"name": "Astoria", "color": "#FF6B00"},
    "ER": {"name": "East River", "color": "#00839C"},
    "RES": {"name": "Rockaway East", "color": "#00A1E1"},
    "RS": {"name": "Rockaway-Soundview", "color": "#4E008E"},
    "RW": {"name": "Rockaway", "color": "#B218AA"},
    "RWS": {"name": "Rockaway West", "color": "#00A1E1"},
    "SB": {"name": "South Brooklyn", "color": "#FFD100"},
    "SG": {"name": "St. George", "color": "#D0006F"},
}


class FerryService:
    def __init__(self, use_local_data: bool = True):
        self.use_local_data = use_local_data
        self.stops: Dict[str, dict] = {}
        self.routes: Dict[str, dict] = {}
        self.trips: Dict[str, dict] = {}
        self.stop_times: List[dict] = []
        self.calendar: Dict[str, dict] = {}
        self._loaded = False
    
    def _load_gtfs_data(self) -> bool:
        """Load GTFS data from local files or download from API"""
        if self._loaded:
            return True
        
        try:
            if self.use_local_data:
                self._load_local_gtfs()
            else:
                self._download_and_load_gtfs()
            self._loaded = True
            return True
        except Exception as e:
            print(f"Error loading GTFS data: {e}")
            return False
    
    def _load_local_gtfs(self):
        """Load GTFS data from local files"""
        # Load stops
        stops_file = os.path.join(LOCAL_GTFS_PATH, "stops.txt")
        if os.path.exists(stops_file):
            with open(stops_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stop_id = row['stop_id'].strip('"')
                    self.stops[stop_id] = {
                        'stop_id': stop_id,
                        'stop_name': row['stop_name'].strip('"'),
                        'stop_lat': float(row['stop_lat']) if row['stop_lat'] else 0,
                        'stop_lon': float(row['stop_lon']) if row['stop_lon'] else 0,
                    }
        
        # Load routes
        routes_file = os.path.join(LOCAL_GTFS_PATH, "routes.txt")
        if os.path.exists(routes_file):
            with open(routes_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    route_id = row['route_id'].strip('"')
                    self.routes[route_id] = {
                        'route_id': route_id,
                        'route_short_name': row['route_short_name'].strip('"'),
                        'route_long_name': row['route_long_name'].strip('"'),
                        'route_color': row.get('route_color', 'FFFFFF').strip('"'),
                    }
        
        # Load trips
        trips_file = os.path.join(LOCAL_GTFS_PATH, "trips.txt")
        if os.path.exists(trips_file):
            with open(trips_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trip_id = row['trip_id'].strip('"')
                    self.trips[trip_id] = {
                        'trip_id': trip_id,
                        'route_id': row['route_id'].strip('"'),
                        'service_id': row['service_id'].strip('"'),
                        'trip_headsign': row.get('trip_headsign', '').strip('"'),
                        'direction_id': row.get('direction_id', '0').strip('"'),
                    }
        
        # Load calendar
        calendar_file = os.path.join(LOCAL_GTFS_PATH, "calendar.txt")
        if os.path.exists(calendar_file):
            with open(calendar_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    service_id = row['service_id'].strip('"')
                    self.calendar[service_id] = {
                        'service_id': service_id,
                        'monday': row['monday'] == '1',
                        'tuesday': row['tuesday'] == '1',
                        'wednesday': row['wednesday'] == '1',
                        'thursday': row['thursday'] == '1',
                        'friday': row['friday'] == '1',
                        'saturday': row['saturday'] == '1',
                        'sunday': row['sunday'] == '1',
                        'start_date': row['start_date'],
                        'end_date': row['end_date'],
                    }
        
        # Load stop_times
        stop_times_file = os.path.join(LOCAL_GTFS_PATH, "stop_times.txt")
        if os.path.exists(stop_times_file):
            with open(stop_times_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.stop_times.append({
                        'trip_id': row['trip_id'].strip('"'),
                        'arrival_time': row['arrival_time'],
                        'departure_time': row['departure_time'],
                        'stop_id': row['stop_id'].strip('"'),
                        'stop_sequence': int(row['stop_sequence']),
                    })
    
    def _download_and_load_gtfs(self):
        """Download GTFS data from NYC Ferry API and parse it"""
        if not REQUESTS_AVAILABLE:
            print("requests library not available. Using local GTFS data.")
            self._load_local_gtfs()
            return
        
        try:
            response = requests.get(GTFS_URL, timeout=30)
            response.raise_for_status()
            
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                # Parse stops.txt
                if 'stops.txt' in zf.namelist():
                    with zf.open('stops.txt') as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                        for row in reader:
                            stop_id = row['stop_id'].strip('"')
                            self.stops[stop_id] = {
                                'stop_id': stop_id,
                                'stop_name': row['stop_name'].strip('"'),
                                'stop_lat': float(row.get('stop_lat', 0) or 0),
                                'stop_lon': float(row.get('stop_lon', 0) or 0),
                            }
                
                # Parse routes.txt
                if 'routes.txt' in zf.namelist():
                    with zf.open('routes.txt') as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                        for row in reader:
                            route_id = row['route_id'].strip('"')
                            self.routes[route_id] = {
                                'route_id': route_id,
                                'route_short_name': row.get('route_short_name', '').strip('"'),
                                'route_long_name': row.get('route_long_name', '').strip('"'),
                                'route_color': row.get('route_color', 'FFFFFF').strip('"'),
                            }
                
                # Parse trips.txt
                if 'trips.txt' in zf.namelist():
                    with zf.open('trips.txt') as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                        for row in reader:
                            trip_id = row['trip_id'].strip('"')
                            self.trips[trip_id] = {
                                'trip_id': trip_id,
                                'route_id': row['route_id'].strip('"'),
                                'service_id': row['service_id'].strip('"'),
                                'trip_headsign': row.get('trip_headsign', '').strip('"'),
                                'direction_id': row.get('direction_id', '0').strip('"'),
                            }
                
                # Parse calendar.txt
                if 'calendar.txt' in zf.namelist():
                    with zf.open('calendar.txt') as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                        for row in reader:
                            service_id = row['service_id'].strip('"')
                            self.calendar[service_id] = {
                                'service_id': service_id,
                                'monday': row['monday'] == '1',
                                'tuesday': row['tuesday'] == '1',
                                'wednesday': row['wednesday'] == '1',
                                'thursday': row['thursday'] == '1',
                                'friday': row['friday'] == '1',
                                'saturday': row['saturday'] == '1',
                                'sunday': row['sunday'] == '1',
                                'start_date': row['start_date'],
                                'end_date': row['end_date'],
                            }
                
                # Parse stop_times.txt
                if 'stop_times.txt' in zf.namelist():
                    with zf.open('stop_times.txt') as f:
                        reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                        for row in reader:
                            self.stop_times.append({
                                'trip_id': row['trip_id'].strip('"'),
                                'arrival_time': row['arrival_time'],
                                'departure_time': row['departure_time'],
                                'stop_id': row['stop_id'].strip('"'),
                                'stop_sequence': int(row['stop_sequence']),
                            })
        except Exception as e:
            print(f"Failed to download GTFS data: {e}. Falling back to local data.")
            self._load_local_gtfs()
    
    def _get_active_service_ids(self, date: datetime.date) -> List[str]:
        """Get service IDs that are active on the given date"""
        active_services = []
        day_of_week = date.weekday()  # 0=Monday, 6=Sunday
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for service_id, cal in self.calendar.items():
            # Check if date is within service range
            start = datetime.datetime.strptime(cal['start_date'], '%Y%m%d').date()
            end = datetime.datetime.strptime(cal['end_date'], '%Y%m%d').date()
            
            if start <= date <= end:
                # Check if service runs on this day of week
                if cal[day_names[day_of_week]]:
                    active_services.append(service_id)
        
        return active_services
    
    def _parse_time(self, time_str: str) -> Optional[datetime.time]:
        """Parse GTFS time string (HH:MM:SS, can be > 24 hours)"""
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2]) if len(parts) > 2 else 0
            
            # Handle times past midnight (e.g., 25:00:00)
            hours = hours % 24
            return datetime.time(hours, minutes, seconds)
        except:
            return None
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert GTFS time string to minutes since midnight"""
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours * 60 + minutes
        except:
            return 0
    
    def get_stop_id_by_name(self, stop_name: str) -> Optional[str]:
        """Find stop ID by stop name (partial match)"""
        self._load_gtfs_data()
        
        stop_name_lower = stop_name.lower()
        for stop_id, stop in self.stops.items():
            if stop_name_lower in stop['stop_name'].lower():
                return stop_id
        return None
    
    def get_all_stops(self) -> List[Dict]:
        """Get list of all ferry stops"""
        self._load_gtfs_data()
        return list(self.stops.values())
    
    def get_all_routes(self) -> List[Dict]:
        """Get list of all ferry routes"""
        self._load_gtfs_data()
        return list(self.routes.values())
    
    def get_next_ferry_times(self, stop_name: str, route_id: Optional[str] = None, count: int = 3) -> List[str]:
        """Get the next ferry departure times for the specified stop.
        
        Args:
            stop_name: Name of the ferry stop (partial match supported)
            route_id: Optional route ID to filter by (e.g., 'ER' for East River)
            count: Number of upcoming departures to return
        
        Returns:
            List of formatted time strings (e.g., ['5 min', '18 min', '32 min'])
        """
        if not self._load_gtfs_data():
            return ["--"] * count
        
        # Find stop ID
        stop_id = self.get_stop_id_by_name(stop_name)
        if not stop_id:
            return ["--"] * count
        
        now = datetime.datetime.now()
        current_date = now.date()
        current_minutes = now.hour * 60 + now.minute
        
        # Get active services for today
        active_services = self._get_active_service_ids(current_date)
        if not active_services:
            return ["--"] * count
        
        # Find upcoming departures from this stop
        upcoming = []
        for st in self.stop_times:
            if st['stop_id'] != stop_id:
                continue
            
            trip = self.trips.get(st['trip_id'])
            if not trip:
                continue
            
            # Check if trip's service is active today
            if trip['service_id'] not in active_services:
                continue
            
            # Filter by route if specified
            if route_id and trip['route_id'] != route_id:
                continue
            
            # Parse departure time
            dep_minutes = self._time_to_minutes(st['departure_time'])
            
            # Only include future departures
            if dep_minutes > current_minutes:
                wait_minutes = dep_minutes - current_minutes
                upcoming.append({
                    'wait_minutes': wait_minutes,
                    'departure_time': st['departure_time'],
                    'route_id': trip['route_id'],
                    'headsign': trip['trip_headsign'],
                })
        
        # Sort by wait time and take the first 'count' departures
        upcoming.sort(key=lambda x: x['wait_minutes'])
        upcoming = upcoming[:count]
        
        # Format results
        results = []
        for dep in upcoming:
            wait = dep['wait_minutes']
            if wait < 1:
                results.append("Boarding")
            elif wait < 2:
                results.append("< 2 min")
            else:
                results.append(f"{wait} min")
        
        # Pad with "--" if not enough departures found
        while len(results) < count:
            results.append("--")
        
        return results
    
    def get_next_ferry_times_detailed(self, stop_name: str, route_id: Optional[str] = None, count: int = 3) -> List[Dict]:
        """Get detailed ferry departure info including route and headsign.
        
        Returns:
            List of dicts with keys: wait_minutes, departure_time, route_id, route_name, headsign
        """
        if not self._load_gtfs_data():
            return []
        
        stop_id = self.get_stop_id_by_name(stop_name)
        if not stop_id:
            return []
        
        now = datetime.datetime.now()
        current_date = now.date()
        current_minutes = now.hour * 60 + now.minute
        
        active_services = self._get_active_service_ids(current_date)
        if not active_services:
            return []
        
        upcoming = []
        for st in self.stop_times:
            if st['stop_id'] != stop_id:
                continue
            
            trip = self.trips.get(st['trip_id'])
            if not trip:
                continue
            
            if trip['service_id'] not in active_services:
                continue
            
            if route_id and trip['route_id'] != route_id:
                continue
            
            dep_minutes = self._time_to_minutes(st['departure_time'])
            
            if dep_minutes > current_minutes:
                wait_minutes = dep_minutes - current_minutes
                route = self.routes.get(trip['route_id'], {})
                upcoming.append({
                    'wait_minutes': wait_minutes,
                    'departure_time': st['departure_time'],
                    'route_id': trip['route_id'],
                    'route_name': route.get('route_long_name', trip['route_id']),
                    'route_color': route.get('route_color', 'FFFFFF'),
                    'headsign': trip['trip_headsign'],
                })
        
        upcoming.sort(key=lambda x: x['wait_minutes'])
        return upcoming[:count]

    def get_ferry_arrivals(self, favorites: Optional[List[Dict[str, str]]] = None) -> Dict[str, List[str]]:
        """Get ferry arrivals for a list of favorite locations.
        
        Each favorite is expected to be a dict with:
            - "location": stop name
            - "route" (optional): route ID to filter by
        
        Returns a dict keyed by location string.
        """
        if favorites is None:
            # Default favorites if none provided
            favorites = [
                {"location": "Wall St/Pier 11"},
                {"location": "East 34th Street"},
            ]
        
        ferry_data: Dict[str, List[str]] = {}
        
        for favorite in favorites:
            location = favorite.get("location", "Unknown Location")
            route_id = favorite.get("route")
            key = location
            arrivals = self.get_next_ferry_times(location, route_id=route_id)
            ferry_data[key] = arrivals
        
        return ferry_data
