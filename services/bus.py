import datetime
import random
from typing import Dict, List
from .config import load_station_config


class BusService:
    def __init__(self):
        pass
        
    def get_realistic_bus_arrivals(self, bus_line: str, location: str, direction: str) -> List[str]:
        """Generate realistic bus arrival times based on current time"""
        current_time = datetime.datetime.now()
        current_second = current_time.second
        
        # Base intervals for different bus types (in minutes)
        bus_intervals = {
            # Manhattan buses - more frequent
            "M": 8,  # M1, M2, M3, etc.
            # Brooklyn buses
            "B": 12,  # B1, B2, B3, etc.
            # Queens buses
            "Q": 15,  # Q1, Q2, Q3, etc.
            # Bronx buses
            "Bx": 10,  # Bx1, Bx2, Bx3, etc.
        }
        
        # Determine bus type from line name
        if bus_line.startswith("M"):
            base_interval = bus_intervals["M"]
        elif bus_line.startswith("B") and not bus_line.startswith("Bx"):
            base_interval = bus_intervals["B"]
        elif bus_line.startswith("Q"):
            base_interval = bus_intervals["Q"]
        elif bus_line.startswith("Bx"):
            base_interval = bus_intervals["Bx"]
        else:
            base_interval = 10  # Default
        
        # Add variation based on time of day
        hour = current_time.hour
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hour
            interval_multiplier = 0.8  # More frequent
        elif 22 <= hour or hour <= 5:  # Late night/early morning
            interval_multiplier = 1.5  # Less frequent
        else:
            interval_multiplier = 1.0  # Normal
        
        adjusted_interval = base_interval * interval_multiplier
        
        # Generate 3 realistic arrival times
        arrivals = []
        for i in range(3):
            # Calculate next arrival time with some randomness
            base_wait = adjusted_interval * (i + 1) * 0.6  # Buses more frequent than multiplier suggests
            random_variation = random.uniform(-2, 3)  # ±2-3 minute variation (buses less predictable)
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
    
    def get_bus_arrivals(self) -> Dict[str, List[str]]:
        """Get bus arrivals for all configured favorites"""
        current_config = load_station_config()
        bus_favorites = current_config.get("bus_favorites", [])
        
        bus_data = {}
        for favorite in bus_favorites:
            bus_line = favorite["bus"]
            location = favorite["location"]
            direction = favorite["direction"]
            key = f"{bus_line}_{location}_{direction}"
            arrivals = self.get_realistic_bus_arrivals(bus_line, location, direction)
            bus_data[key] = arrivals
            
        return bus_data
