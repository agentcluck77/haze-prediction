"""
ERA5 CSV weather data loader.
Loads pre-processed ERA5 weather grid for fast training access.
"""

import pandas as pd
from pathlib import Path
from src.features.geospatial import haversine_distance

# Path to ERA5 CSV file
ERA5_CSV_FILE = Path(__file__).parent.parent.parent / "data" / "weather" / "era5_grid.csv"

# Global cache
_ERA5_CACHE = None
_GRID_POINTS_CACHE = None


def load_era5_csv():
    """
    Load ERA5 weather data from CSV.

    Returns:
        tuple: (weather_df, grid_points_list)
    """
    global _ERA5_CACHE, _GRID_POINTS_CACHE

    if _ERA5_CACHE is not None:
        return _ERA5_CACHE, _GRID_POINTS_CACHE

    print("Loading ERA5 weather data from CSV...")

    if not ERA5_CSV_FILE.exists():
        raise FileNotFoundError(f"ERA5 CSV not found: {ERA5_CSV_FILE}")

    df = pd.read_csv(ERA5_CSV_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Extract unique grid points
    grid_points = df[['grid_lat', 'grid_lon']].drop_duplicates()
    grid_points_list = [(row['grid_lat'], row['grid_lon']) for _, row in grid_points.iterrows()]

    print(f"Loaded {len(df):,} weather records for {len(grid_points_list)} grid points")
    print(f"Memory usage: ~{df.memory_usage(deep=True).sum() / (1024**2):.1f} MB")

    _ERA5_CACHE = df
    _GRID_POINTS_CACHE = grid_points_list

    return df, grid_points_list


def clear_cache():
    """Clear the ERA5 cache to free memory"""
    global _ERA5_CACHE, _GRID_POINTS_CACHE
    _ERA5_CACHE = None
    _GRID_POINTS_CACHE = None
    print("ERA5 cache cleared")
