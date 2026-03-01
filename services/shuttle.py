import datetime
from typing import Dict, List
from .config import SHUTTLE_TIMING


class ShuttleService:
    def __init__(self):
        pass
        
    def get_next_shuttle_times(self, location: str) -> List[str]:
        """Get the next 3 shuttle times for the specified location"""
        if location not in SHUTTLE_TIMING:
            return ["--", "--", "--"]
            
        current_time = datetime.datetime.now()
        shuttle_times = SHUTTLE_TIMING[location]
        next_times = []
        
        # Convert current time to minutes since midnight for comparison
        current_total_minutes = current_time.hour * 60 + current_time.minute
        
        for time_str in shuttle_times:
            try:
                # Parse shuttle time
                shuttle_time = datetime.datetime.strptime(time_str, "%I:%M %p")
                shuttle_total_minutes = shuttle_time.hour * 60 + shuttle_time.minute
                
                # If shuttle time is later today, add it
                if shuttle_total_minutes > current_total_minutes:
                    next_times.append(time_str)
                    if len(next_times) >= 3:
                        break
            except ValueError:
                continue
        
        # If we don't have enough times (end of day), add tomorrow's first times
        if len(next_times) < 3:
            remaining_needed = 3 - len(next_times)
            for i in range(min(remaining_needed, len(shuttle_times))):
                next_times.append(f"{shuttle_times[i]} (Next Day)")
        
        # Ensure we always return exactly 3 items
        while len(next_times) < 3:
            next_times.append("--")
        
        return next_times[:3]
    
    def get_shuttle_arrivals(self) -> Dict[str, List[str]]:
        """Get shuttle arrivals for HP Shuttle location"""
        shuttle_data = {}
        location = "10 Halletts Point"
        shuttle_data[location] = self.get_next_shuttle_times(location)
        return shuttle_data
