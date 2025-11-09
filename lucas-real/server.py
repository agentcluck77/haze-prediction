from flask import Flask, jsonify, send_from_directory
import openmeteo_requests
import requests_cache
from retry_requests import retry
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__, static_folder='static')

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def fetch_wind_point(lat, lon, url):
    """Fetch wind data for a single point"""
    params = {
        "latitude": float(lat),
        "longitude": float(lon),
        "current": ["wind_speed_10m", "wind_direction_10m"],
    }

    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        current = response.Current()
        wind_speed = current.Variables(0).Value()
        wind_direction = current.Variables(1).Value()

        return {
            "lat": float(lat),
            "lon": float(lon),
            "speed": float(wind_speed) if not np.isnan(wind_speed) else 0,
            "direction": float(wind_direction) if not np.isnan(wind_direction) else 0
        }
    except Exception as e:
        print(f"Error fetching data for {lat}, {lon}: {e}")
        return None

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/wind', methods=['GET'])
def get_wind_data():
    """
    Fetch wind data for a grid of locations using concurrent requests
    Returns wind speed and direction for visualization
    Accepts query parameters: south, north, west, east, zoom
    """
    from flask import request

    # Get bounds from query parameters (if provided)
    lat_min = float(request.args.get('south', -5.0))
    lat_max = float(request.args.get('north', 8.0))
    lon_min = float(request.args.get('west', 95.0))
    lon_max = float(request.args.get('east', 110.0))
    zoom = int(request.args.get('zoom', 6))

    # Calculate grid size based on zoom level
    # Higher zoom = more dense grid, but cap to avoid rate limits
    # Zoom 5-6: 12x12 = 144 points
    # Zoom 7-8: 15x15 = 225 points
    # Zoom 9-10: 18x18 = 324 points
    # Zoom 11+: 20x20 = 400 points
    if zoom <= 6:
        grid_size = 12
    elif zoom <= 8:
        grid_size = 15
    elif zoom <= 10:
        grid_size = 18
    else:
        grid_size = 20
    lats = np.linspace(lat_min, lat_max, grid_size)
    lons = np.linspace(lon_min, lon_max, grid_size)

    url = "https://api.open-meteo.com/v1/forecast"

    wind_data = []

    # Create list of all coordinate pairs
    coordinates = [(lat, lon) for lat in lats for lon in lons]

    print(f"Fetching wind data for {len(coordinates)} points using {min(20, len(coordinates))} concurrent threads...")

    # Use ThreadPoolExecutor for concurrent API calls
    # Limit to 20 concurrent threads to avoid overwhelming the API and hitting rate limits
    with ThreadPoolExecutor(max_workers=20) as executor:
        # Submit all tasks
        future_to_coords = {
            executor.submit(fetch_wind_point, lat, lon, url): (lat, lon)
            for lat, lon in coordinates
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_coords):
            result = future.result()
            if result is not None:
                wind_data.append(result)
            completed += 1
            if completed % 500 == 0:
                print(f"Completed {completed}/{len(coordinates)} requests...")

    print(f"Successfully fetched {len(wind_data)}/{len(coordinates)} data points")

    return jsonify({
        "data": wind_data,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
