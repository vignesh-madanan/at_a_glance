import json
import os
import pandas as pd
from typing import Dict, List

# CONFIGURATION FILE PATHS
CONFIG_FILE = "station_config.json"
STATIONS_FILE = "Stations.csv"

# DEFAULT STATION AND LINES CONFIGURATION
DEFAULT_STATION_CONFIG = {
    "train_favorites": [
        {"station": "Union Square - 14th St", "line": "4", "direction": "Downtown", "css_class": "line-4-5-6"},
        {"station": "Union Square - 14th St", "line": "4", "direction": "Uptown", "css_class": "line-4-5-6"},
        {"station": "Union Square - 14th St", "line": "6", "direction": "Downtown", "css_class": "line-4-5-6"},
        {"station": "Union Square - 14th St", "line": "6", "direction": "Uptown", "css_class": "line-4-5-6"},
        {"station": "Times Sq - 42 St", "line": "N", "direction": "Downtown", "css_class": "line-n-q-r-w"},
        {"station": "Times Sq - 42 St", "line": "Q", "direction": "Uptown", "css_class": "line-n-q-r-w"}
    ],
    "bus_favorites": [
        {"bus": "M14A", "location": "14th St & Union Sq E", "direction": "Eastbound"},
        {"bus": "M14D", "location": "14th St & Union Sq E", "direction": "Westbound"},
        {"bus": "M101", "location": "3rd Ave & 14th St", "direction": "Uptown"},
        {"bus": "M103", "location": "3rd Ave & 14th St", "direction": "Downtown"}
    ],
    "ferry_favorites": [
        {"location": "Wall St/Pier 11", "route": None},
        {"location": "East 34th Street", "route": None}
    ]
}

# SUBWAY LINE DEFINITIONS
SUBWAY_LINES = {
    "4": {"name": "4", "css_class": "line-4-5-6"},
    "5": {"name": "5", "css_class": "line-4-5-6"},
    "6": {"name": "6", "css_class": "line-4-5-6"},
    "6X": {"name": "6X", "css_class": "line-4-5-6"},
    "N": {"name": "N", "css_class": "line-n-q-r-w"},
    "Q": {"name": "Q", "css_class": "line-n-q-r-w"},
    "R": {"name": "R", "css_class": "line-n-q-r-w"},
    "W": {"name": "W", "css_class": "line-n-q-r-w"},
    "L": {"name": "L", "css_class": "line-l"},
    "1": {"name": "1", "css_class": "line-1-2-3"},
    "2": {"name": "2", "css_class": "line-1-2-3"},
    "3": {"name": "3", "css_class": "line-1-2-3"},
    "A": {"name": "A", "css_class": "line-a-c-e"},
    "C": {"name": "C", "css_class": "line-a-c-e"},
    "E": {"name": "E", "css_class": "line-a-c-e"},
    "B": {"name": "B", "css_class": "line-b-d-f-m"},
    "D": {"name": "D", "css_class": "line-b-d-f-m"},
    "F": {"name": "F", "css_class": "line-b-d-f-m"},
    "M": {"name": "M", "css_class": "line-b-d-f-m"},
    "G": {"name": "G", "css_class": "line-g"},
    "J": {"name": "J", "css_class": "line-j-z"},
    "Z": {"name": "Z", "css_class": "line-j-z"},
    "7": {"name": "7", "css_class": "line-7"},
    "7X": {"name": "7X", "css_class": "line-7"},
    "S": {"name": "S", "css_class": "line-s"}
}

DIRECTIONS = [
    "Downtown & Brooklyn",
    "Uptown & Bronx", 
    "Uptown & Manhattan",
    "Downtown",
    "Uptown",
    "Brooklyn",
    "Queens",
    "Manhattan",
    "Bronx"
]

# COMMON NYC BUS LINES
COMMON_BUS_LINES = [
    "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12", "M14A", "M14D", 
    "M15", "M16", "M17", "M18", "M19", "M20", "M21", "M22", "M23", "M26", "M27", "M28", "M29", 
    "M30", "M31", "M34", "M35", "M42", "M50", "M55", "M57", "M58", "M60", "M66", "M72", "M79", 
    "M86", "M96", "M98", "M100", "M101", "M102", "M103", "M104", "M106", "M116", "M125",
    "Bx1", "Bx2", "Bx3", "Bx4", "Bx5", "Bx6", "Bx7", "Bx8", "Bx9", "Bx10", "Bx11", "Bx12", 
    "Bx15", "Bx17", "Bx19", "Bx21", "Bx22", "Bx23", "Bx25", "Bx26", "Bx27", "Bx28", "Bx29", 
    "Bx30", "Bx31", "Bx32", "Bx33", "Bx34", "Bx35", "Bx36", "Bx39", "Bx40", "Bx41", "Bx42",
    "B1", "B2", "B3", "B4", "B6", "B7", "B8", "B9", "B10", "B11", "B12", "B13", "B14", "B15", 
    "B16", "B17", "B20", "B24", "B25", "B26", "B31", "B32", "B35", "B36", "B37", "B38", "B39", 
    "B41", "B42", "B43", "B44", "B45", "B46", "B47", "B48", "B49", "B52", "B54", "B57", "B60", 
    "B61", "B62", "B63", "B64", "B65", "B67", "B68", "B69", "B70", "B74", "B82", "B83", "B84",
    "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12", "Q13", "Q15", 
    "Q16", "Q17", "Q18", "Q19", "Q20", "Q21", "Q22", "Q23", "Q24", "Q25", "Q26", "Q27", "Q28", 
    "Q29", "Q30", "Q31", "Q32", "Q33", "Q34", "Q35", "Q36", "Q37", "Q38", "Q39", "Q40", "Q41", 
    "Q42", "Q43", "Q44", "Q45", "Q46", "Q47", "Q48", "Q49", "Q50", "Q52", "Q53", "Q54", "Q55", 
    "Q56", "Q58", "Q59", "Q60", "Q64", "Q65", "Q66", "Q67", "Q69", "Q70", "Q72", "Q74", "Q76", 
    "Q77", "Q83", "Q84", "Q85", "Q88", "Q100", "Q101", "Q102", "Q103", "Q104"
]

BUS_DIRECTIONS = [
    "Northbound",
    "Southbound", 
    "Eastbound",
    "Westbound",
    "Uptown",
    "Downtown",
    "To Manhattan",
    "To Brooklyn",
    "To Queens", 
    "To Bronx"
]

# NYC FERRY STOPS (common ones)
FERRY_STOPS = [
    "Wall St/Pier 11",
    "East 34th Street",
    "Hunters Point South",
    "Greenpoint",
    "North Williamsburg",
    "South Williamsburg",
    "Dumbo/Fulton Ferry",
    "Atlantic Ave/BBP Pier 6",
    "Red Hook/Atlantic Basin",
    "Sunset Park/BAT",
    "Bay Ridge",
    "Astoria",
    "Roosevelt Island",
    "East 90th St",
    "Soundview",
    "Ferry Point Park",
    "Rockaway",
    "Governors Island",
    "St. George",
    "Battery Park City/Vesey St.",
    "Midtown West/W 39th St-Pier 79",
    "Brooklyn Navy Yard",
    "Stuyvesant Cove",
    "Corlears Hook",
    "Long Island City",
]

# NYC FERRY ROUTES
FERRY_ROUTES = [
    {"id": "AS", "name": "Astoria", "color": "#FF6B00"},
    {"id": "ER", "name": "East River", "color": "#00839C"},
    {"id": "RES", "name": "Rockaway East", "color": "#00A1E1"},
    {"id": "RS", "name": "Rockaway-Soundview", "color": "#4E008E"},
    {"id": "RW", "name": "Rockaway", "color": "#B218AA"},
    {"id": "RWS", "name": "Rockaway West", "color": "#00A1E1"},
    {"id": "SB", "name": "South Brooklyn", "color": "#FFD100"},
    {"id": "SG", "name": "St. George", "color": "#D0006F"},
]

SHUTTLE_TIMING = {
    '10 Halletts Point': [
        "5:30 AM",
        "6:00 AM",
        "6:30 AM",
        "7:00 AM",
        "7:30 AM",
        "8:00 AM",
        "8:30 AM",
        "9:00 AM",
        "9:30 AM",
        "10:00 AM",
        "11:00 AM",
        "11:30 AM",
        "12:00 PM",
        "12:30 PM",
        "1:00 PM",
        "1:30 PM",
        "2:00 PM",
        "2:30 PM",
        "3:00 PM",
        "4:00 PM",
        "4:30 PM",
        "5:00 PM",
        "5:30 PM",
        "6:00 PM",
        "6:30 PM",
        "7:00 PM",
        "7:30 PM"],
    "30th Ave & 31st St": [
        "5:45 AM",
        "6:15 AM",
        "6:45 AM",
        "7:15 AM",
        "7:45 AM",
        "8:15 AM",
        "8:45 AM",
        "9:15 AM",
        "9:45 AM",
        "10:15 AM",
        "11:15 AM",
        "11:45 AM",
        "12:15 PM",
        "12:45 PM",
        "1:15 PM",
        "1:45 PM",
        "2:15 PM",
        "2:45 PM",
        "3:15 PM",
        "4:15 PM",
        "4:45 PM",
        "5:15 PM",
        "5:45 PM",
        "6:15 PM",
        "6:45 PM",
        "7:15 PM",
        "7:45 PM"]
}


def load_station_config():
    """Load station configuration from file or return default"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_STATION_CONFIG

def save_station_config(config):
    """Save station configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_stations_list():
    """Load stations list from CSV or JSON file without ordering"""
    # Try CSV first if it exists
    try:
        if os.path.exists(STATIONS_FILE):
            df = pd.read_csv(STATIONS_FILE)
            station_names = df['Stop Name'].unique().tolist()
            return station_names
    except Exception:
        pass

    # Fallback to JSON stations file if available
    try:
        json_path = "stations.json"
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
            station_names = data.get("subway_stations", [])
            if station_names:
                return station_names
    except Exception:
        pass

    # Final hard-coded fallback
    return ["Union Square - 14th St", "Times Sq - 42 St", "Grand Central - 42 St"]
