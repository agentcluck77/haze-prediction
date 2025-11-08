"""
Grid-based weather data loader.
Loads pre-downloaded weather grid and assigns weather to fires based on nearest grid point.
"""

import pandas as pd
from pathlib import Path
import numpy as np
from src.features.geospatial import haversine_distance


# Path to grid weather data
WEATHER_GRID_FILE = Path(__file__).parent.parent.parent / "data" / "weather_grid" / "weather_grid.csv"

# Global cache for grid weather data
_GRID_WEATHER_CACHE = None
_GRID_POINTS_CACHE = None


def load_grid_weather():
    """
    Load grid weather data from local CSV file into memory.

    Returns:
        tuple: (grid_weather_df, grid_points_list)
            - grid_weather_df: DataFrame with all weather data
            - grid_points_list: List of unique (lat, lon) grid points
    """
    global _GRID_WEATHER_CACHE, _GRID_POINTS_CACHE

    # Return cached data if already loaded
    if _GRID_WEATHER_CACHE is not None:
        return _GRID_WEATHER_CACHE, _GRID_POINTS_CACHE

    print("Loading grid weather data from local CSV file...")

    if not WEATHER_GRID_FILE.exists():
        print(f"ERROR: Grid weather file not found: {WEATHER_GRID_FILE}")
        print("Please run: python3 scripts/download_grid_weather.py")
        return None, None

    df = pd.read_csv(WEATHER_GRID_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Extract unique grid points
    grid_points = df[['grid_lat', 'grid_lon']].drop_duplicates()
    grid_points_list = [(row['grid_lat'], row['grid_lon']) for _, row in grid_points.iterrows()]

    print(f"Loaded {len(df):,} weather records for {len(grid_points_list)} grid points")
    print(f"Memory usage: ~{df.memory_usage(deep=True).sum() / (1024**2):.1f} MB")

    # Cache for future use
    _GRID_WEATHER_CACHE = df
    _GRID_POINTS_CACHE = grid_points_list

    return df, grid_points_list


def find_nearest_grid_point(lat, lon, grid_points):
    """
    Find the nearest grid point to a given location.

    Args:
        lat: Target latitude
        lon: Target longitude
        grid_points: List of (grid_lat, grid_lon) tuples

    Returns:
        tuple: (grid_lat, grid_lon) of nearest point
    """
    target_pos = (lat, lon)
    min_distance = float('inf')
    nearest_point = grid_points[0]

    for grid_lat, grid_lon in grid_points:
        grid_pos = (grid_lat, grid_lon)
        distance = haversine_distance(target_pos, grid_pos)

        if distance < min_distance:
            min_distance = distance
            nearest_point = (grid_lat, grid_lon)

    return nearest_point


def get_weather_for_location(lat, lon, timestamp, forecast_hours=168):
    """
    Get weather forecast for a specific location.

    Finds the nearest grid point and returns its weather.

    Args:
        lat: Latitude
        lon: Longitude
        timestamp: Starting timestamp
        forecast_hours: Hours of forecast needed

    Returns:
        pandas.DataFrame: Weather forecast for nearest grid point
    """
    # Load grid weather (uses cache)
    grid_weather, grid_points = load_grid_weather()

    if grid_weather is None or len(grid_points) == 0:
        return pd.DataFrame()

    # Find nearest grid point
    grid_lat, grid_lon = find_nearest_grid_point(lat, lon, grid_points)

    # Filter to this grid point
    point_weather = grid_weather[
        (grid_weather['grid_lat'] == grid_lat) &
        (grid_weather['grid_lon'] == grid_lon)
    ]

    # Filter to requested time range
    end_timestamp = timestamp + pd.Timedelta(hours=forecast_hours)
    weather_slice = point_weather[
        (point_weather['timestamp'] >= timestamp) &
        (point_weather['timestamp'] < end_timestamp)
    ].copy()

    return weather_slice


def get_weather_dict_for_fires(fires_df, timestamp, forecast_hours=168):
    """
    Get weather for all unique fire locations as a dict.

    Groups fires by nearest grid point and returns weather for each.

    Args:
        fires_df: DataFrame with fire locations
        timestamp: Starting timestamp
        forecast_hours: Hours of forecast needed

    Returns:
        dict: Mapping from grid_id to weather DataFrame
    """
    if len(fires_df) == 0:
        return {}

    # Load grid weather (uses cache)
    grid_weather, grid_points = load_grid_weather()

    if grid_weather is None or len(grid_points) == 0:
        return {}

    # Find unique grid points needed for all fires
    fire_grid_points = set()
    for _, fire in fires_df.iterrows():
        grid_lat, grid_lon = find_nearest_grid_point(
            fire['latitude'],
            fire['longitude'],
            grid_points
        )
        fire_grid_points.add((grid_lat, grid_lon))

    # Get weather for each unique grid point
    weather_dict = {}
    end_timestamp = timestamp + pd.Timedelta(hours=forecast_hours)

    for grid_lat, grid_lon in fire_grid_points:
        grid_id = f"{grid_lat}_{grid_lon}"

        # Filter to this grid point and time range
        weather_slice = grid_weather[
            (grid_weather['grid_lat'] == grid_lat) &
            (grid_weather['grid_lon'] == grid_lon) &
            (grid_weather['timestamp'] >= timestamp) &
            (grid_weather['timestamp'] < end_timestamp)
        ].copy()

        if len(weather_slice) >= 24:  # Need at least 24h of data
            weather_dict[grid_id] = weather_slice

    return weather_dict


def clear_cache():
    """Clear the grid weather cache."""
    global _GRID_WEATHER_CACHE, _GRID_POINTS_CACHE
    _GRID_WEATHER_CACHE = None
    _GRID_POINTS_CACHE = None
    print("Grid weather cache cleared")
