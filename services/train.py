import streamlit as st
import datetime
import random
from typing import Dict, List, Optional
from .config import load_station_config, SUBWAY_LINES


class SubwayService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or st.secrets.get("mta_api_key", "")
        
    def get_realistic_arrivals(self, station_name: str, line: str, direction: str) -> List[str]:
        """Generate realistic train arrival times based on current time"""
        current_time = datetime.datetime.now()
        current_minute = current_time.minute
        current_second = current_time.second
        
        # Base intervals for different lines (in minutes)
        line_intervals = {
            "1": 5, "2": 4, "3": 5, "4": 3, "5": 4, "6": 3,
            "7": 4, "A": 6, "B": 8, "C": 8, "D": 6, "E": 5,
            "F": 6, "G": 10, "J": 8, "L": 4, "M": 8, "N": 6,
            "Q": 5, "R": 6, "W": 8, "Z": 10, "S": 15
        }
        
        # Get base interval for this line (default 6 minutes)
        base_interval = line_intervals.get(line, 6)
        
        # Add some variation based on time of day
        hour = current_time.hour
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hour
            interval_multiplier = 0.7  # More frequent
        elif 22 <= hour or hour <= 5:  # Late night/early morning
            interval_multiplier = 2.0  # Less frequent
        else:
            interval_multiplier = 1.0  # Normal
        
        adjusted_interval = base_interval * interval_multiplier
        
        # Generate 3 realistic arrival times
        arrivals = []
        for i in range(3):
            # Calculate next arrival time with some randomness
            base_wait = adjusted_interval * (i + 1)
            random_variation = random.uniform(-1.5, 1.5)  # ±1.5 minute variation
            total_wait = base_wait + random_variation
            
            # Subtract current seconds to make it more realistic
            total_wait -= current_second / 60.0
            
            if total_wait < 0.5:
                arrivals.append("Arriving")
            elif total_wait < 1:
                arrivals.append("< 1 min")
            else:
                arrivals.append(f"{int(total_wait)} min")
        
        return arrivals

    def get_mock_arrivals(self, favorites_only=False) -> Dict[str, List[str]]:
        """Mock subway data for demonstration with realistic timing"""
        mock_data = {}
        
        if favorites_only:
            # Get current configuration for favorites
            current_config = load_station_config()
            train_favorites = current_config.get("train_favorites", [])
            
            for favorite in train_favorites:
                station = favorite["station"]
                line = favorite["line"]
                direction = favorite["direction"]
                key = f"{station}_{line}_{direction}"
                arrivals = self.get_realistic_arrivals(station, line, direction)
                mock_data[key] = arrivals
        else:
            # All possible trains for various stations
            all_lines_directions = [
                ("Union Square - 14th St", "1", "Uptown & Bronx"),
                ("Union Square - 14th St", "1", "Downtown & Brooklyn"),
                ("Union Square - 14th St", "4", "Uptown & Bronx"),
                ("Union Square - 14th St", "4", "Downtown & Brooklyn"),
                ("Union Square - 14th St", "6", "Uptown & Bronx"),
                ("Union Square - 14th St", "6", "Downtown & Brooklyn"),
                ("Times Sq - 42 St", "N", "Uptown & Manhattan"),
                ("Times Sq - 42 St", "N", "Downtown & Brooklyn"),
                ("Times Sq - 42 St", "Q", "Uptown & Manhattan"),
                ("Times Sq - 42 St", "Q", "Downtown & Brooklyn"),
                ("Times Sq - 42 St", "R", "Uptown & Manhattan"),
                ("Times Sq - 42 St", "R", "Downtown & Brooklyn"),
                ("Grand Central - 42 St", "4", "Uptown & Bronx"),
                ("Grand Central - 42 St", "4", "Downtown & Brooklyn"),
                ("Grand Central - 42 St", "6", "Uptown & Bronx"),
                ("Grand Central - 42 St", "6", "Downtown & Brooklyn"),
            ]
            
            for station, line, direction in all_lines_directions:
                key = f"{station}_{line}_{direction}"
                arrivals = self.get_realistic_arrivals(station, line, direction)
                mock_data[key] = arrivals
            
        return mock_data
        
    def get_arrivals(self, favorites_only=False) -> Dict[str, List[str]]:
        if not self.api_key:
            return self.get_mock_arrivals(favorites_only)
            
        # Real MTA API integration would go here
        # For now, return mock data
        return self.get_mock_arrivals(favorites_only)
