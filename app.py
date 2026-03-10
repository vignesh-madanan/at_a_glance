import streamlit as st
import requests
import datetime
import time
import json
import os
import pandas as pd
from typing import Dict, List, Optional
import pytz

# NYC timezone
NYC_TZ = pytz.timezone('America/New_York')

def get_nyc_time():
    """Get current time in NYC timezone"""
    return datetime.datetime.now(NYC_TZ)

# Import configurations and utilities from services
from services.config import (
    load_station_config, save_station_config, load_stations_list,
    SUBWAY_LINES, DIRECTIONS, COMMON_BUS_LINES, BUS_DIRECTIONS,
    FERRY_STOPS, FERRY_ROUTES
)
from services.train import SubwayService
from services.bus import BusService
from services.shuttle import ShuttleService
from services.ferry import FerryService
from services.alerts import AlertsService
from services.langgraph_agent import chat as agent_chat



# Load current configuration
STATION_CONFIG = load_station_config()

# Page configuration
st.set_page_config(
    page_title="NYC Subway Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get help': None,
        'Report a bug': None,
        'About': "NYC Subway Dashboard - E-ink Display"
    }
)

# Force sidebar to stay expanded
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'expanded'

# Custom CSS for E-ink display optimization
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap');
    
    .main > div {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: none;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    .stApp {
        background-color: white;
        color: black;
    }
    
    /* Header styling with centered masthead */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 3px solid black;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    
    .header-center {
        text-align: center;
        flex: 1;
    }
    
    .masthead-title {
        font-family: 'Georgia', 'Times New Roman', serif;
        font-size: 2rem;
        font-style: italic;
        color: #666;
        letter-spacing: 0.03em;
        margin: 0 auto;
        line-height: 1;
        text-align: center;
        display: block;
    }
    
    .masthead-subtitle {
        font-family: 'Georgia', 'Times New Roman', serif;
        font-size: 0.7rem;
        font-style: italic;
        color: #666;
        margin-top: 3px;
        letter-spacing: 0.03em;
        text-align: center;
        display: block;
    }
    
    .time-display {
        font-size: 2.5rem;
        font-weight: bold;
        color: black;
    }
    
    .date-display {
        font-size: 1.2rem;
        color: black;
        margin-top: 5px;
    }
    
    .weather-display {
        text-align: right;
    }
    
    .temperature {
        font-size: 2rem;
        font-weight: bold;
        color: black;
    }
    
    .weather-desc {
        font-size: 1rem;
        color: black;
        margin-top: 5px;
    }
    
    /* Section header styling */
    .station-name {
        font-size: 1rem;
        font-weight: bold;
        text-align: left;
        color: black;
        border-bottom: 2px solid #ddd;
        padding-bottom: 6px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Compact row layout - reduced whitespace */
    .line-container {
        margin-bottom: 8px;
        border: none;
        border-left: 4px solid #ccc;
        padding: 6px 10px;
        background-color: transparent;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .line-container.train-row { border-left-color: #00933c; background-color: rgba(0, 147, 60, 0.05); }
    .line-container.bus-row { border-left-color: #ff6319; background-color: rgba(255, 99, 25, 0.05); }
    .line-container.shuttle-row { border-left-color: #9c27b0; background-color: rgba(156, 39, 176, 0.05); }
    .line-container.ferry-row { border-left-color: #00839C; background-color: rgba(0, 131, 156, 0.05); }
    
    .line-header {
        display: flex;
        align-items: center;
        min-width: 180px;
        flex-shrink: 0;
    }
    
    /* Larger, bolder route badges */
    .line-badge {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        color: white;
        margin-right: 8px;
        font-size: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        flex-shrink: 0;
    }
    
    .line-4-5-6 { 
        background-color: #00933c; 
    }
    
    .line-n-q-r-w { 
        background-color: #fccc0a; 
        color: black !important;
    }
    
    .line-l { 
        background-color: #a7a9ac; 
    }
    
    .line-1-2-3 { 
        background-color: #ee352e; 
    }
    
    .line-a-c-e { 
        background-color: #0039a6; 
    }
    
    .line-b-d-f-m { 
        background-color: #ff6319; 
    }
    
    .line-g { 
        background-color: #6cbe45; 
    }
    
    .line-j-z { 
        background-color: #996633; 
    }
    
    .line-7 { 
        background-color: #b933ad; 
    }
    
    .line-s { 
        background-color: #808183; 
    }
    
    .direction-text {
        font-size: 0.85rem;
        font-weight: 600;
        color: #333;
        line-height: 1.2;
    }
    
    .direction-text strong {
        color: black;
    }
    
    /* Section styling - compact with distinct colors */
    .favorites-section {
        background-color: white;
        border: none;
        border-top: 4px solid #00933c;
        border-radius: 0;
        padding: 10px 12px;
        margin-bottom: 12px;
        margin-left: 0;
        margin-right: 0;
    }
    
    .bus-favorites-section {
        background-color: white;
        border: none;
        border-top: 4px solid #ff6319;
        border-radius: 0;
        padding: 10px 12px;
        margin-bottom: 12px;
        margin-left: 0;
        margin-right: 0;
    }
    
    .shuttle-favorites-section {
        background-color: white;
        border: none;
        border-top: 4px solid #9c27b0;
        border-radius: 0;
        padding: 10px 12px;
        margin-bottom: 12px;
        margin-left: 0;
        margin-right: 0;
    }
    
    .ferry-favorites-section {
        background-color: white;
        border: none;
        border-top: 4px solid #00839C;
        border-radius: 0;
        padding: 10px 12px;
        margin-bottom: 12px;
        margin-left: 0;
        margin-right: 0;
    }
    
    .ferry-badge {
        width: 42px;
        height: 42px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        color: white;
        margin-right: 8px;
        font-size: 0.75rem;
        background-color: #00839C;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        flex-shrink: 0;
    }
    
    .bus-badge {
        width: 42px;
        height: 42px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        color: white;
        margin-right: 8px;
        font-size: 1.3rem;
        background-color: #ff6319;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        flex-shrink: 0;
    }
    
    .shuttle-badge {
        width: 42px;
        height: 42px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        color: white;
        margin-right: 8px;
        font-size: 0.85rem;
        background-color: #9c27b0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        flex-shrink: 0;
    }
    
    .arrivals-container {
        display: flex;
        gap: 6px;
        margin-left: 0;
        flex-wrap: nowrap;
        justify-content: flex-start;
        flex: 1;
    }
    
    /* Primary arrival time - large countdown */
    .arrival-time {
        padding: 4px 8px;
        border: none;
        background-color: transparent;
        color: black;
        text-align: center;
        min-width: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .arrival-countdown {
        font-size: 1.6rem;
        font-weight: 900;
        color: black;
        line-height: 1;
    }
    
    .arrival-eta {
        font-size: 0.85rem;
        color: #333;
        font-weight: 600;
        margin-top: 3px;
    }
    
    .arrival-dest {
        font-size: 0.6rem;
        color: #888;
        font-weight: normal;
    }
    
    /* Status badges */
    .status-badge {
        font-size: 0.6rem;
        padding: 2px 6px;
        border-radius: 3px;
        font-weight: bold;
        margin-top: 2px;
    }
    
    .status-ontime {
        background-color: #4CAF50;
        color: white;
    }
    
    .status-delayed {
        background-color: #f44336;
        color: white;
    }
    
    .status-arriving {
        background-color: #2196F3;
        color: white;
    }
    
    .last-updated {
        text-align: left;
        font-size: 0.8rem;
        color: #666;
        margin-top: 10px;
        display: flex;
        align-items: center;
    }
    
    .bottom-controls {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 20px;
        padding-top: 10px;
        border-top: 1px solid #ddd;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stDeployButton {display:none;}
    .stDecoration {display:none;}
    
    /* Mobile Responsive Styles */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        
        /* Force Streamlit columns to stack vertically on mobile */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        
        .stHorizontalBlock {
            flex-wrap: wrap !important;
        }
        
        /* Header stacks vertically on mobile */
        .header-container {
            flex-direction: column;
            text-align: center;
            gap: 10px;
        }
        
        .time-display {
            font-size: 1.8rem;
        }
        
        .date-display {
            font-size: 0.9rem;
        }
        
        .masthead-title {
            font-size: 1.5rem;
        }
        
        .masthead-subtitle {
            font-size: 0.6rem;
        }
        
        .weather-display {
            text-align: center;
        }
        
        .temperature {
            font-size: 1.5rem;
        }
        
        /* Section headers smaller on mobile */
        .station-name {
            font-size: 0.9rem;
        }
        
        /* Compact line rows on mobile */
        .line-container {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
            padding: 8px;
        }
        
        .line-header {
            min-width: auto;
            width: 100%;
        }
        
        .line-badge {
            width: 36px;
            height: 36px;
            font-size: 1.2rem;
        }
        
        .bus-badge, .shuttle-badge, .ferry-badge {
            width: 36px;
            height: 36px;
            font-size: 0.7rem;
        }
        
        .direction-text {
            font-size: 0.8rem;
        }
        
        /* Arrivals wrap and stay readable */
        .arrivals-container {
            width: 100%;
            flex-wrap: wrap;
            justify-content: flex-start;
            gap: 8px;
        }
        
        .arrival-time {
            min-width: 70px;
        }
        
        .arrival-countdown {
            font-size: 1.3rem;
        }
        
        .arrival-eta {
            font-size: 0.75rem;
        }
        
        /* Section padding reduced */
        .favorites-section,
        .bus-favorites-section,
        .shuttle-favorites-section,
        .ferry-favorites-section {
            padding: 8px;
            margin-bottom: 8px;
        }
    }
    
    /* Extra small screens */
    @media (max-width: 480px) {
        .time-display {
            font-size: 1.5rem;
        }
        
        .masthead-title {
            font-size: 1.2rem;
        }
        
        .line-badge {
            width: 32px;
            height: 32px;
            font-size: 1rem;
        }
        
        .arrival-countdown {
            font-size: 1.1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

class WeatherService:
    def __init__(self):
        # NYC coordinates (Central Park)
        self.latitude = 40.7829
        self.longitude = -73.9654
        
    def get_weather(self) -> Dict:
        try:
            # Open-Meteo API - completely free, no API key required
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current_weather=true&temperature_unit=fahrenheit"
            
            response = requests.get(url, timeout=5)
            data = response.json()
            
            current_weather = data["current_weather"]
            temperature = round(current_weather["temperature"])
            
            # Weather code mapping (WMO Weather interpretation codes) with emojis
            weather_codes = {
                0: ("Clear sky", "☀️"),
                1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"), 3: ("Overcast", "☁️"),
                45: ("Fog", "🌫️"), 48: ("Depositing rime fog", "🌫️"),
                51: ("Light drizzle", "🌦️"), 53: ("Moderate drizzle", "🌦️"), 55: ("Dense drizzle", "🌧️"),
                56: ("Light freezing drizzle", "🌨️"), 57: ("Dense freezing drizzle", "🌨️"),
                61: ("Slight rain", "🌧️"), 63: ("Moderate rain", "🌧️"), 65: ("Heavy rain", "⛈️"),
                66: ("Light freezing rain", "🌨️"), 67: ("Heavy freezing rain", "🌨️"),
                71: ("Slight snow", "🌨️"), 73: ("Moderate snow", "❄️"), 75: ("Heavy snow", "❄️"),
                77: ("Snow grains", "🌨️"),
                80: ("Slight rain showers", "🌦️"), 81: ("Moderate rain showers", "🌧️"), 82: ("Violent rain showers", "⛈️"),
                85: ("Slight snow showers", "🌨️"), 86: ("Heavy snow showers", "❄️"),
                95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm with slight hail", "⛈️"), 99: ("Thunderstorm with heavy hail", "⛈️")
            }
            
            weather_code = current_weather.get("weathercode", 0)
            description, emoji = weather_codes.get(weather_code, ("Unknown", "🌡️"))
            
            return {
                "temperature": str(temperature),
                "description": description,
                "emoji": emoji
            }
            
        except Exception as e:
            # Fallback to demo data if API fails
            return {
                "temperature": "72",
                "description": "Clear (API unavailable)",
                "emoji": "☀️"
            }




def render_header():
    """Render the header with time, masthead, and weather"""
    now = get_nyc_time()
    
    weather_service = WeatherService()
    weather_data = weather_service.get_weather()
    
    st.markdown(f"""
    <div class="header-container">
        <div class="time-section">
            <div class="time-display">{now.strftime("%I:%M %p")}</div>
            <div class="date-display">{now.strftime("%A, %B %d, %Y")}</div>
        </div>
        <div class="header-center">
            <h1 class="masthead-title">At a Glance</h1>
            <div class="masthead-subtitle">"All the Transit That's Fit to this Page"</div>
        </div>
        <div class="weather-display">
            <div class="temperature">{weather_data['emoji']} {weather_data['temperature']}°F</div>
            <div class="weather-desc">{weather_data['description']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_subway_line(line: str, direction: str, arrivals: List[str], line_class: str):
    """Render a single subway line with arrivals"""
    arrivals_html = "".join([f'<div class="arrival-time">{time}</div>' for time in arrivals])
    
    st.markdown(f"""
    <div class="line-container">
        <div class="line-header">
            <div class="line-badge {line_class}">{line}</div>
            <div class="direction-text">{direction}</div>
        </div>
        <div class="arrivals-container">
            {arrivals_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_subway_line_with_station(station: str, line: str, direction: str, arrivals: List[str], line_class: str):
    """Render a single subway line with arrivals and station name"""
    # Generate arrival times with ETA and train details
    arrivals_with_details = []
    current_time = get_nyc_time()
    
    # Define final stations for each line and direction
    final_stations = {
        "4": {"Downtown": "Utica Av", "Uptown": "Woodlawn", "Downtown & Brooklyn": "Utica Av", "Uptown & Bronx": "Woodlawn"},
        "5": {"Downtown": "Flatbush Av", "Uptown": "Dyre Av", "Downtown & Brooklyn": "Flatbush Av", "Uptown & Bronx": "Dyre Av"},
        "6": {"Downtown": "Brooklyn Bridge", "Uptown": "Pelham Bay Park", "Downtown & Brooklyn": "Brooklyn Bridge", "Uptown & Bronx": "Pelham Bay Park"},
        "N": {"Downtown": "Coney Island", "Uptown": "Astoria", "Downtown & Brooklyn": "Coney Island", "Uptown & Manhattan": "Astoria"},
        "Q": {"Downtown": "Coney Island", "Uptown": "96 St", "Downtown & Brooklyn": "Coney Island", "Uptown & Manhattan": "96 St"},
        "R": {"Downtown": "Bay Ridge", "Uptown": "Forest Hills", "Downtown & Brooklyn": "Bay Ridge", "Uptown & Manhattan": "Forest Hills"},
        "W": {"Downtown": "Whitehall", "Uptown": "Astoria", "Downtown & Brooklyn": "Whitehall", "Uptown & Manhattan": "Astoria"},
        "L": {"Brooklyn": "Canarsie", "Manhattan": "8 Av"},
        "1": {"Downtown": "South Ferry", "Uptown": "Van Cortlandt Park", "Downtown & Brooklyn": "South Ferry", "Uptown & Bronx": "Van Cortlandt Park"},
        "2": {"Downtown": "Flatbush Av", "Uptown": "Wakefield", "Downtown & Brooklyn": "Flatbush Av", "Uptown & Bronx": "Wakefield"},
        "3": {"Downtown": "New Lots Av", "Uptown": "Harlem", "Downtown & Brooklyn": "New Lots Av", "Uptown & Bronx": "Harlem"}
    }
    
    final_station = final_stations.get(line, {}).get(direction, "Terminal")
    
    for arrival_text in arrivals:
        eta_text = ""
        status_class = "status-ontime"
        status_text = "On Time"
        
        if arrival_text == "Arriving":
            eta_text = current_time.strftime("%I:%M %p")
            status_class = "status-arriving"
            status_text = "Arriving"
        elif arrival_text == "< 1 min":
            eta_time = current_time + datetime.timedelta(minutes=1)
            eta_text = eta_time.strftime("%I:%M %p")
            status_class = "status-arriving"
            status_text = "< 1 min"
        elif arrival_text.endswith(" min"):
            try:
                minutes = int(arrival_text.split()[0])
                eta_time = current_time + datetime.timedelta(minutes=minutes)
                eta_text = eta_time.strftime("%I:%M %p")
            except:
                eta_text = "--"
        elif arrival_text == "--":
            eta_text = "--"
            status_class = ""
            status_text = ""
        else:
            eta_text = "--"
        
        arrivals_with_details.append((arrival_text, eta_text, final_station, status_class, status_text))
    
    # Build HTML with large countdown and small ETA
    arrivals_html_parts = []
    for time, eta, final_station, status_class, status_text in arrivals_with_details:
        arrivals_html_parts.append(f'''<div class="arrival-time">
            <span class="arrival-countdown">{time}</span>
            <span class="arrival-eta">{eta}</span>
        </div>''')
    
    arrivals_html = "".join(arrivals_html_parts)
    
    st.markdown(f"""
    <div class="line-container train-row">
        <div class="line-header">
            <div class="line-badge {line_class}">{line}</div>
            <div class="direction-text">{line} to {direction}<br><strong>{station}</strong></div>
        </div>
        <div class="arrivals-container">
            {arrivals_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_bus_line(bus: str, location: str, direction: str, arrivals: List[str]):
    """Render a single bus line with arrivals and location"""
    arrivals_with_eta = []
    current_time = get_nyc_time()
    
    for arrival_text in arrivals:
        eta_text = ""
        if arrival_text == "Arriving":
            eta_text = current_time.strftime("%I:%M %p")
        elif arrival_text == "< 1 min":
            eta_time = current_time + datetime.timedelta(minutes=1)
            eta_text = eta_time.strftime("%I:%M %p")
        elif arrival_text.endswith(" min"):
            try:
                minutes = int(arrival_text.split()[0])
                eta_time = current_time + datetime.timedelta(minutes=minutes)
                eta_text = eta_time.strftime("%I:%M %p")
            except:
                eta_text = "--"
        else:
            eta_text = "--"
        
        arrivals_with_eta.append((arrival_text, eta_text))
    
    arrivals_html = "".join([
        f'''<div class="arrival-time">
            <span class="arrival-countdown">{time}</span>
            <span class="arrival-eta">{eta}</span>
        </div>''' 
        for time, eta in arrivals_with_eta
    ])
    
    st.markdown(f"""
    <div class="line-container bus-row">
        <div class="line-header">
            <div class="bus-badge">{bus}</div>
            <div class="direction-text">{bus} {direction}<br><strong>{location}</strong></div>
        </div>
        <div class="arrivals-container">
            {arrivals_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_train_favorites_section():
    """Render the train favorites section"""
    st.markdown('''
    <div class="favorites-section">
        <div class="station-name">🚇 Favorite Trains</div>
    ''', unsafe_allow_html=True)
    
    subway_service = SubwayService()
    arrivals_data = subway_service.get_arrivals(favorites_only=True)
    
    current_config = load_station_config()
    train_favorites = current_config.get("train_favorites", [])
    
    if not train_favorites:
        st.markdown('<div style="text-align: center; color: #666; padding: 20px;">No train favorites configured.<br>Use the admin panel to add favorites.</div>', unsafe_allow_html=True)
    else:
        for favorite in train_favorites:
            station = favorite["station"]
            line = favorite["line"]
            direction = favorite["direction"]
            css_class = favorite["css_class"]
            
            key = f"{station}_{line}_{direction}"
            arrivals = arrivals_data.get(key, ["--", "--", "--"])
            render_subway_line_with_station(station, line, direction, arrivals, css_class)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_shuttle_line(location: str, arrivals: List[str]):
    """Render a single shuttle line with arrivals and location"""
    # Generate arrival times with ETA
    arrivals_with_eta = []
    current_time = get_nyc_time()
    
    for arrival_text in arrivals:
        eta_text = ""
        if arrival_text == "--":
            eta_text = "--"
        elif "(Next Day)" in arrival_text:
            # Remove (Next Day) for ETA calculation
            clean_time = arrival_text.replace(" (Next Day)", "")
            try:
                arrival_time = datetime.datetime.strptime(clean_time, "%I:%M %p")
                # Add one day
                tomorrow = current_time.replace(hour=arrival_time.hour, minute=arrival_time.minute, second=0, microsecond=0) + datetime.timedelta(days=1)
                eta_text = tomorrow.strftime("%I:%M %p")
            except:
                eta_text = "Tomorrow"
        else:
            try:
                arrival_time = datetime.datetime.strptime(arrival_text, "%I:%M %p")
                today_arrival = current_time.replace(hour=arrival_time.hour, minute=arrival_time.minute, second=0, microsecond=0)
                eta_text = today_arrival.strftime("%I:%M %p")
            except:
                eta_text = "--"
        
        arrivals_with_eta.append((arrival_text, eta_text))
    
    arrivals_html = "".join([
        f'''<div class="arrival-time">
            <span class="arrival-countdown">{time}</span>
            <span class="arrival-eta">{eta}</span>
        </div>''' 
        for time, eta in arrivals_with_eta
    ])
    
    st.markdown(f"""
    <div class="line-container shuttle-row">
        <div class="line-header">
            <div class="shuttle-badge">HP</div>
            <div class="direction-text">HP Shuttle<br><strong>{location}</strong></div>
        </div>
        <div class="arrivals-container">
            {arrivals_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_shuttle_favorites_section():
    """Render the HP Shuttle section"""
    st.markdown('''
    <div class="shuttle-favorites-section">
        <div class="station-name">🚐 HP Shuttle</div>
    ''', unsafe_allow_html=True)
    
    shuttle_service = ShuttleService()
    arrivals_data = shuttle_service.get_shuttle_arrivals()
    
    location = "10 Halletts Point"
    arrivals = arrivals_data.get(location, ["--", "--", "--"])
    render_shuttle_line(location, arrivals)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_ferry_line(location: str, arrivals: List[str], route_info: Optional[List[dict]] = None):
    """Render a single ferry line with arrivals and location"""
    arrivals_with_eta = []
    current_time = get_nyc_time()
    
    for i, arrival_text in enumerate(arrivals):
        eta_text = ""
        route_name = ""
        headsign = ""
        
        # Get route info if available
        if route_info and i < len(route_info):
            route_name = route_info[i].get('route_name', '')
            headsign = route_info[i].get('headsign', '')
        
        if arrival_text == "--":
            eta_text = "--"
        elif arrival_text == "Boarding":
            eta_text = current_time.strftime("%I:%M %p")
        elif arrival_text == "< 2 min":
            eta_time = current_time + datetime.timedelta(minutes=2)
            eta_text = eta_time.strftime("%I:%M %p")
        elif arrival_text.endswith(" min"):
            try:
                minutes = int(arrival_text.split()[0])
                eta_time = current_time + datetime.timedelta(minutes=minutes)
                eta_text = eta_time.strftime("%I:%M %p")
            except:
                eta_text = "--"
        else:
            eta_text = "--"
        
        arrivals_with_eta.append((arrival_text, eta_text, route_name, headsign))
    
    # Build HTML for each arrival with large countdown
    arrivals_html_parts = []
    for time, eta, route_name, headsign in arrivals_with_eta:
        headsign_html = f'<span class="arrival-dest">to {headsign}</span>' if headsign and time != "--" else ""
        
        arrivals_html_parts.append(f'''<div class="arrival-time">
            <span class="arrival-countdown">{time}</span>
            <span class="arrival-eta">{eta}</span>{headsign_html}
        </div>''')
    
    arrivals_html = "".join(arrivals_html_parts)
    
    st.markdown(f"""
    <div class="line-container ferry-row">
        <div class="line-header">
            <div class="ferry-badge">⛴️</div>
            <div class="direction-text">NYC Ferry<br><strong>{location}</strong></div>
        </div>
        <div class="arrivals-container">
            {arrivals_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_ferry_favorites_section():
    """Render the ferry favorites section"""
    st.markdown('''
    <div class="ferry-favorites-section">
        <div class="station-name">⛴️ NYC Ferry</div>
    ''', unsafe_allow_html=True)
    
    ferry_service = FerryService(use_local_data=True)
    
    current_config = load_station_config()
    ferry_favorites = current_config.get("ferry_favorites", [
        {"location": "Wall St/Pier 11"},
        {"location": "East 34th Street"}
    ])
    
    if not ferry_favorites:
        st.markdown('<div style="text-align: center; color: #666; padding: 20px;">No ferry favorites configured.</div>', unsafe_allow_html=True)
    else:
        for favorite in ferry_favorites:
            location = favorite.get("location", "Unknown")
            route_id = favorite.get("route")
            
            # Get simple arrival times
            arrivals = ferry_service.get_next_ferry_times(location, route_id=route_id)
            # Get detailed info for headsigns
            detailed = ferry_service.get_next_ferry_times_detailed(location, route_id=route_id, count=3)
            
            render_ferry_line(location, arrivals, detailed)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_bus_favorites_section():
    """Render the bus favorites section"""
    st.markdown('''
    <div class="bus-favorites-section">
        <div class="station-name">🚌 Favorite Buses</div>
    ''', unsafe_allow_html=True)
    
    bus_service = BusService()
    arrivals_data = bus_service.get_bus_arrivals()
    
    current_config = load_station_config()
    bus_favorites = current_config.get("bus_favorites", [])
    
    if not bus_favorites:
        st.markdown('<div style="text-align: center; color: #666; padding: 20px;">No bus favorites configured.<br>Use the admin panel to add favorites.</div>', unsafe_allow_html=True)
    else:
        for favorite in bus_favorites:
            bus = favorite["bus"]
            location = favorite["location"]
            direction = favorite["direction"]
            
            key = f"{bus}_{location}_{direction}"
            arrivals = arrivals_data.get(key, ["--", "--", "--"])
            render_bus_line(bus, location, direction, arrivals)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_alerts_section():
    """Render MTA service alerts below the header, filtered to configured favorites."""
    config = load_station_config()

    # Collect route IDs from configured favorites
    favorite_routes = []
    for fav in config.get("trains", []):
        line = fav.get("line", "")
        if line:
            favorite_routes.append(line)
    for fav in config.get("buses", []):
        bus = fav.get("bus", "")
        if bus:
            favorite_routes.append(bus)

    alerts = AlertsService().get_service_alerts(routes=favorite_routes if favorite_routes else None)

    for alert in alerts:
        routes_label = ", ".join(alert["routes"]) if alert["routes"] else "All Lines"
        header = alert["header"] or alert["effect"] or "Service Alert"
        description = alert["description"]
        message = f"**[{routes_label}]** {header}"
        if description and description != header:
            # Truncate long descriptions to keep the section compact
            desc_short = description[:160].rstrip()
            if len(description) > 160:
                desc_short += "…"
            message += f" — {desc_short}"
        st.warning(message)


def render_navigator_page():
    """Render the NYC Transit Navigator chat page."""
    st.title("🗺️ NYC Transit Navigator")
    st.caption("Ask me anything about getting around NYC — subway, bus, or ferry.")

    # Initialize chat history in session state
    if "navigator_history" not in st.session_state:
        st.session_state.navigator_history = []

    # Display chat messages
    for msg in st.session_state.navigator_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggested starter questions (only shown when history is empty)
    if not st.session_state.navigator_history:
        st.markdown("**Try asking:**")
        starters = [
            "How do I get from Union Square to JFK?",
            "What's the fastest way to get to Williamsburg from Midtown?",
            "Are there any delays on the L train right now?",
            "What time is the next ferry from Wall St/Pier 11?",
            "How much does a 30-day MetroCard cost?",
        ]
        cols = st.columns(2)
        for i, q in enumerate(starters):
            if cols[i % 2].button(q, key=f"starter_{i}"):
                # Treat starter click as a user message
                st.session_state.navigator_history.append({"role": "user", "content": q})
                with st.spinner("Thinking…"):
                    reply = agent_chat(st.session_state.navigator_history[:-1], q)
                st.session_state.navigator_history.append({"role": "assistant", "content": reply})
                st.rerun()

    # Chat input at the bottom
    user_input = st.chat_input("Ask about subway, bus, ferry, routes, fares…")
    if user_input:
        st.session_state.navigator_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                reply = agent_chat(st.session_state.navigator_history[:-1], user_input)
            st.markdown(reply)
        st.session_state.navigator_history.append({"role": "assistant", "content": reply})

    # Clear chat button
    if st.session_state.navigator_history:
        if st.button("🗑️ Clear conversation", key="clear_chat"):
            st.session_state.navigator_history = []
            st.rerun()


def render_admin_page():
    """Render the admin configuration page"""
    st.title("🔧 Station Configuration")
    
    # Load available stations
    available_stations = load_stations_list()
    
    # Current configuration
    current_config = load_station_config()
    
    # Initialize favorites if not in session state
    if 'admin_train_favorites' not in st.session_state:
        st.session_state.admin_train_favorites = current_config.get("train_favorites", [])
    if 'admin_bus_favorites' not in st.session_state:
        st.session_state.admin_bus_favorites = current_config.get("bus_favorites", [])
    if 'admin_ferry_favorites' not in st.session_state:
        st.session_state.admin_ferry_favorites = current_config.get("ferry_favorites", [])
    
    # Create tabs for trains, buses, and ferries
    tab1, tab2, tab3 = st.tabs(["🚇 Train Favorites", "🚌 Bus Favorites", "⛴️ Ferry Favorites"])
    
    with tab1:
        st.write("Configure up to 6 favorite train lines from any station:")
        
        # Add/Remove train favorite buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if len(st.session_state.admin_train_favorites) < 6:
                if st.button("➕ Add Train", key="add_train_btn"):
                    st.session_state.admin_train_favorites.append({
                        "station": "Union Square - 14th St",
                        "line": "4",
                        "direction": "Downtown",
                        "css_class": "line-4-5-6"
                    })
                    st.rerun()
            else:
                st.button("➕ Add Train", disabled=True, key="add_train_btn_disabled")
                st.caption("Maximum 6 favorites reached")
        
        with col2:
            if len(st.session_state.admin_train_favorites) > 0:
                if st.button("🗑️ Remove Last Train", key="remove_last_train"):
                    st.session_state.admin_train_favorites.pop()
                    st.rerun()
        
        with col3:
            st.write(f"**Train Favorites: {len(st.session_state.admin_train_favorites)}/6**")
        
        # Display and edit train favorites
        for i, favorite in enumerate(st.session_state.admin_train_favorites):
            st.write(f"**Train {i+1}:**")
            col1, col2, col3, col4 = st.columns([3, 2, 3, 2])
            
            with col1:
                # Station dropdown
                try:
                    current_station_idx = available_stations.index(favorite["station"])
                except ValueError:
                    current_station_idx = 0
                    
                new_station = st.selectbox(
                    "Station:",
                    available_stations,
                    index=current_station_idx,
                    key=f"train_station_{i}"
                )
                
            with col2:
                # Line dropdown
                line_options = list(SUBWAY_LINES.keys())
                try:
                    current_line_idx = line_options.index(favorite["line"])
                except ValueError:
                    current_line_idx = 0
                
                new_line = st.selectbox(
                    "Line:",
                    line_options,
                    index=current_line_idx,
                    key=f"train_line_{i}"
                )
                
            with col3:
                # Direction dropdown
                try:
                    current_dir_idx = DIRECTIONS.index(favorite["direction"])
                except ValueError:
                    current_dir_idx = 0
                
                new_direction = st.selectbox(
                    "Direction:",
                    DIRECTIONS,
                    index=current_dir_idx,
                    key=f"train_direction_{i}"
                )
                
            with col4:
                # Auto-assign CSS class based on line
                new_css_class = SUBWAY_LINES[new_line]["css_class"]
                st.text_input(
                    "CSS:",
                    value=new_css_class,
                    disabled=True,
                    key=f"train_css_{i}"
                )
            
            # Update the train favorite config
            st.session_state.admin_train_favorites[i] = {
                "station": new_station,
                "line": new_line,
                "direction": new_direction,
                "css_class": new_css_class
            }
            
            st.divider()
    
    with tab2:
        st.write("Configure up to 6 favorite bus lines with their locations:")
        
        # Add/Remove bus favorite buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if len(st.session_state.admin_bus_favorites) < 6:
                if st.button("➕ Add Bus", key="add_bus_btn"):
                    st.session_state.admin_bus_favorites.append({
                        "bus": "M14A",
                        "location": "14th St & Union Sq E",
                        "direction": "Eastbound"
                    })
                    st.rerun()
            else:
                st.button("➕ Add Bus", disabled=True, key="add_bus_btn_disabled")
                st.caption("Maximum 6 favorites reached")
        
        with col2:
            if len(st.session_state.admin_bus_favorites) > 0:
                if st.button("🗑️ Remove Last Bus", key="remove_last_bus"):
                    st.session_state.admin_bus_favorites.pop()
                    st.rerun()
        
        with col3:
            st.write(f"**Bus Favorites: {len(st.session_state.admin_bus_favorites)}/6**")
        
        # Display and edit bus favorites
        for i, favorite in enumerate(st.session_state.admin_bus_favorites):
            st.write(f"**Bus {i+1}:**")
            col1, col2, col3 = st.columns([2, 4, 2])
            
            with col1:
                # Bus line dropdown
                try:
                    current_bus_idx = COMMON_BUS_LINES.index(favorite["bus"])
                except ValueError:
                    current_bus_idx = 0
                    
                new_bus = st.selectbox(
                    "Bus:",
                    COMMON_BUS_LINES,
                    index=current_bus_idx,
                    key=f"bus_line_{i}"
                )
                
            with col2:
                # Location text input
                new_location = st.text_input(
                    "Location:",
                    value=favorite["location"],
                    key=f"bus_location_{i}",
                    help="e.g., '14th St & Union Sq E', '3rd Ave & 14th St'"
                )
                
            with col3:
                # Direction dropdown
                try:
                    current_dir_idx = BUS_DIRECTIONS.index(favorite["direction"])
                except ValueError:
                    current_dir_idx = 0
                
                new_direction = st.selectbox(
                    "Direction:",
                    BUS_DIRECTIONS,
                    index=current_dir_idx,
                    key=f"bus_direction_{i}"
                )
            
            # Update the bus favorite config
            st.session_state.admin_bus_favorites[i] = {
                "bus": new_bus,
                "location": new_location,
                "direction": new_direction
            }
            
            st.divider()
    
    with tab3:
        st.write("Configure up to 6 favorite ferry stops:")
        
        # Add/Remove ferry favorite buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if len(st.session_state.admin_ferry_favorites) < 6:
                if st.button("➕ Add Ferry Stop", key="add_ferry_btn"):
                    st.session_state.admin_ferry_favorites.append({
                        "location": "Wall St/Pier 11",
                        "route": None
                    })
                    st.rerun()
            else:
                st.button("➕ Add Ferry Stop", disabled=True, key="add_ferry_btn_disabled")
                st.caption("Maximum 6 favorites reached")
        
        with col2:
            if len(st.session_state.admin_ferry_favorites) > 0:
                if st.button("🗑️ Remove Last Ferry", key="remove_last_ferry"):
                    st.session_state.admin_ferry_favorites.pop()
                    st.rerun()
        
        with col3:
            st.write(f"**Ferry Favorites: {len(st.session_state.admin_ferry_favorites)}/6**")
        
        # Display and edit ferry favorites
        for i, favorite in enumerate(st.session_state.admin_ferry_favorites):
            st.write(f"**Ferry Stop {i+1}:**")
            col1, col2 = st.columns([3, 2])
            
            with col1:
                # Ferry stop dropdown
                try:
                    current_stop_idx = FERRY_STOPS.index(favorite["location"])
                except ValueError:
                    current_stop_idx = 0
                    
                new_location = st.selectbox(
                    "Stop:",
                    FERRY_STOPS,
                    index=current_stop_idx,
                    key=f"ferry_stop_{i}"
                )
                
            with col2:
                # Route filter dropdown (optional)
                route_options = ["All Routes"] + [f"{r['id']} - {r['name']}" for r in FERRY_ROUTES]
                current_route = favorite.get("route")
                
                if current_route:
                    try:
                        # Find the route in the list
                        route_idx = next((idx + 1 for idx, r in enumerate(FERRY_ROUTES) if r['id'] == current_route), 0)
                    except:
                        route_idx = 0
                else:
                    route_idx = 0
                
                new_route_selection = st.selectbox(
                    "Route (optional):",
                    route_options,
                    index=route_idx,
                    key=f"ferry_route_{i}",
                    help="Filter by specific ferry route or show all"
                )
                
                # Extract route ID from selection
                if new_route_selection == "All Routes":
                    new_route = None
                else:
                    new_route = new_route_selection.split(" - ")[0]
            
            # Update the ferry favorite config
            st.session_state.admin_ferry_favorites[i] = {
                "location": new_location,
                "route": new_route
            }
            
            st.divider()
    
    # Save and preview buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save Configuration", type="primary", key="save_config"):
            # Build new configuration
            new_config = {
                "train_favorites": st.session_state.admin_train_favorites,
                "bus_favorites": st.session_state.admin_bus_favorites,
                "ferry_favorites": st.session_state.admin_ferry_favorites
            }
            
            # Save configuration
            save_station_config(new_config)
            
            # Update global config
            global STATION_CONFIG
            STATION_CONFIG = new_config
            
            st.success("✅ Configuration saved successfully!")
            st.balloons()
            
    with col2:
        if st.button("👁️ Preview", key="preview_config"):
            st.subheader("Preview Configuration")
            
            st.write("**Train Favorites:**")
            for i, favorite in enumerate(st.session_state.admin_train_favorites):
                st.write(f"{i+1}. {favorite['station']} - Line {favorite['line']} ({favorite['direction']})")
            
            st.write("**Bus Favorites:**")
            for i, favorite in enumerate(st.session_state.admin_bus_favorites):
                st.write(f"{i+1}. Bus {favorite['bus']} at {favorite['location']} ({favorite['direction']})")
            
            st.write("**Ferry Favorites:**")
            for i, favorite in enumerate(st.session_state.admin_ferry_favorites):
                route_str = f" ({favorite['route']})" if favorite.get('route') else " (All Routes)"
                st.write(f"{i+1}. Ferry at {favorite['location']}{route_str}")
    
    # Current configuration display
    st.subheader("Current Active Configuration")
    st.json(current_config)
    
    # Navigation
    if st.button("🏠 Back to Dashboard", type="secondary", key="back_to_dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def _render_sidebar():
    """Render the persistent left navigation sidebar."""
    with st.sidebar:
        st.markdown("## 🚇 At a Glance")
        st.divider()

        def nav_button(label: str, page: str):
            is_active = st.session_state.get("page") == page
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{page}", use_container_width=True, type=btn_type):
                st.session_state.page = page
                st.rerun()

        nav_button("🏠  Dashboard", "dashboard")
        nav_button("🗺️  NYC Navigator", "navigator")
        nav_button("⚙️  Settings", "admin")

        st.divider()

        # Auto-refresh control (only relevant on dashboard)
        if st.session_state.get("page") == "dashboard":
            st.subheader("Auto-refresh")
            auto_refresh = st.checkbox("Enable auto-refresh", value=True, key="auto_refresh_chk")
            st.caption("Refresh interval: 30 seconds")
            return auto_refresh

        return False


def main():
    """Main application function"""
    # Initialize page state
    if 'page' not in st.session_state:
        st.session_state.page = "dashboard"

    # Check for admin page navigation from query params
    if st.query_params.get("page") == "admin":
        st.session_state.page = "admin"
        st.rerun()

    auto_refresh = _render_sidebar()

    if st.session_state.page == "admin":
        render_admin_page()
        return

    if st.session_state.page == "navigator":
        render_navigator_page()
        return
    
    # Auto-refresh logic (only for dashboard)
    if st.session_state.page == "dashboard":
        # Render header with masthead
        render_header()

        # Service alerts (shows nothing if no active alerts or no API key)
        render_alerts_section()

        # Top row: Favorite Trains and HP Shuttle
        top_col1, top_col2 = st.columns([1, 1], gap="large")
        
        with top_col1:
            render_train_favorites_section()
            
        with top_col2:
            render_shuttle_favorites_section()
        
        # Bottom row: Favorite Buses and NYC Ferry
        bottom_col1, bottom_col2 = st.columns([1, 1], gap="large")
        
        with bottom_col1:
            render_bus_favorites_section()
        
        with bottom_col2:
            render_ferry_favorites_section()
        
        # Bottom controls section
        last_updated = get_nyc_time().strftime("%I:%M %p")
        
        st.markdown(f'''
        <div class="bottom-controls">
            <div class="last-updated">Last updated: {last_updated}</div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Auto-refresh mechanism - 30 second intervals
        if auto_refresh:
            time.sleep(30)
            st.rerun()

if __name__ == "__main__":
    main()