# NYC Subway Dashboard for E-ink Display

A Streamlit web application designed for 1024x640 E-ink displays showing NYC subway times, weather, and current time.

## Features

- **Real-time Clock**: Current time and date
- **Weather Information**: NYC temperature and conditions
- **NYC Subway Times**: Live arrival times for Union Square station
- **E-ink Optimized**: High contrast, minimal colors, readable fonts
- **Auto-refresh**: Updates every 30 seconds

## Setup

1. Install dependencies using `uv` and `make`:
```bash
make setup
```

2. Add API keys to `.streamlit/secrets.toml`:
   - Get weather API key from [OpenWeatherMap](https://openweathermap.org/api)
   - Get MTA API key from [MTA Developer Resources](https://api.mta.info/)

3. Run the Streamlit UI:
```bash
make ui
```

4. (Optional) Run a separate backend (if you add one):
```bash
make backend
```

5. Open in browser and navigate to: `http://localhost:8501`

## Configuration

- **Display Size**: Optimized for 1024x640 resolution
- **Station**: Currently set to Union Square - 14th St
- **Subway Lines**: 4, 6, N, Q, L trains
- **Weather Location**: NYC coordinates (40.7128, -74.0060)

## Demo Mode

The app runs with mock data when API keys are not provided, perfect for testing the interface.

## Browser Setup for E-ink

For best E-ink display results:
1. Set browser to fullscreen mode (F11)
2. Hide browser UI elements
3. Ensure 1024x640 viewport size