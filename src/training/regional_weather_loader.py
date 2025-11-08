"""
Regional weather data loader.
Loads pre-downloaded weather for fire regions and assigns weather to fires.
"""

import pandas as pd
from pathlib import Path
import numpy as np
from src.features.geospatial import haversine_distance


# Path to regional weather data
WEATHER_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "weather_regional"

# Fire region definitions (must match download script)
FIRE_REGIONS = [
    {'name': 'West_Sumatra', 'lat': -0.5, 'lon': 100.5},
    {'name': 'Central_Sumatra', 'lat': -2.0, 'lon': 102.0},
    {'name': 'South_Sumatra', 'lat': -3.5, 'lon': 104.0},
    {'name': 'Kalimantan', 'lat': -1.5, 'lon': 110.0},
    {'name': 'Peninsular_Malaysia', 'lat': 3.5, 'lon': 101.5}
]

# Global cache for regional weather data
_REGIONAL_WEATHER_CACHE = None


def load_all_regional_weather():
    """
    Load all regional weather data from local CSV files into memory.

    Returns:
        dict: Dictionary mapping region name to DataFrame
            {region_name: DataFrame with columns [timestamp, wind_speed_10m, wind_direction_10m, ...]}
    """
    global _REGIONAL_WEATHER_CACHE

    # Return cached data if already loaded
    if _REGIONAL_WEATHER_CACHE is not None:
        return _REGIONAL_WEATHER_CACHE

    print("Loading regional weather data from local CSV files...")

    regional_weather = {}

    for region in FIRE_REGIONS:
        csv_file = WEATHER_DATA_DIR / f"{region['name']}.csv"

        if not csv_file.exists():
            print(f"WARNING: Weather file not found for {region['name']}: {csv_file}")
            continue

        df = pd.read_csv(csv_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        regional_weather[region['name']] = df

        print(f"  Loaded {len(df):,} weather records for {region['name']}")

    if len(regional_weather) == 0:
        print(f"ERROR: No regional weather data found in {WEATHER_DATA_DIR}")
        print("Please run: python3 scripts/download_regional_weather.py")
        return {}

    print(f"Loaded weather for {len(regional_weather)} regions")

    # Cache for future use
    _REGIONAL_WEATHER_CACHE = regional_weather

    return regional_weather


def assign_fires_to_regions(fires_df):
    """
    Assign each fire to its nearest region.

    Args:
        fires_df: DataFrame with columns [latitude, longitude, ...]

    Returns:
        pandas.Series: Region name for each fire
    """
    if len(fires_df) == 0:
        return pd.Series([], dtype=str)

    regions = []

    for _, fire in fires_df.iterrows():
        fire_pos = (fire['latitude'], fire['longitude'])

        # Find nearest region
        min_distance = float('inf')
        nearest_region = FIRE_REGIONS[0]['name']

        for region in FIRE_REGIONS:
            region_pos = (region['lat'], region['lon'])
            distance = haversine_distance(fire_pos, region_pos)

            if distance < min_distance:
                min_distance = distance
                nearest_region = region['name']

        regions.append(nearest_region)

    return pd.Series(regions, index=fires_df.index)


def get_weather_for_fire_location(fire_lat, fire_lon, timestamp, forecast_hours=168):
    """
    Get weather forecast for a fire location.

    Finds the nearest region and returns its weather forecast.

    Args:
        fire_lat: Fire latitude
        fire_lon: Fire longitude
        timestamp: Starting timestamp
        forecast_hours: Hours of forecast needed

    Returns:
        pandas.DataFrame: Weather forecast for the region
    """
    # Load regional weather (uses cache)
    regional_weather = load_all_regional_weather()

    if len(regional_weather) == 0:
        return pd.DataFrame()

    # Find nearest region
    fire_pos = (fire_lat, fire_lon)
    min_distance = float('inf')
    nearest_region = None

    for region in FIRE_REGIONS:
        region_pos = (region['lat'], region['lon'])
        distance = haversine_distance(fire_pos, region_pos)

        if distance < min_distance:
            min_distance = distance
            nearest_region = region['name']

    if nearest_region is None or nearest_region not in regional_weather:
        return pd.DataFrame()

    # Get weather for this region
    region_weather = regional_weather[nearest_region]

    # Filter to requested time range
    end_timestamp = timestamp + pd.Timedelta(hours=forecast_hours)
    weather_slice = region_weather[
        (region_weather['timestamp'] >= timestamp) &
        (region_weather['timestamp'] < end_timestamp)
    ].copy()

    return weather_slice


def get_singapore_weather(timestamp, forecast_hours=168):
    """
    Get weather forecast for Singapore.

    Singapore is closest to Peninsular_Malaysia region.

    Args:
        timestamp: Starting timestamp
        forecast_hours: Hours of forecast needed

    Returns:
        pandas.DataFrame: Weather forecast
    """
    return get_weather_for_fire_location(
        fire_lat=1.3521,
        fire_lon=103.8198,
        timestamp=timestamp,
        forecast_hours=forecast_hours
    )


def clear_cache():
    """Clear the regional weather cache."""
    global _REGIONAL_WEATHER_CACHE
    _REGIONAL_WEATHER_CACHE = None
    print("Regional weather cache cleared")
