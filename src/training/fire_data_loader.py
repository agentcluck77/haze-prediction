"""
Historical fire data loader from local MODIS or VIIRS CSV files.
Implements Option 1: Load all data into memory for fast lookups.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import os


# Get satellite data source from environment or use default
FIRE_DATA_SOURCE = os.getenv('FIRE_DATA_SOURCE', 'FIRM_MODIS')
FIRE_DATA_DIR = Path(__file__).parent.parent.parent / "data" / FIRE_DATA_SOURCE

# Global cache for fire data (loaded once)
_FIRE_DATA_CACHE = None


def load_all_historical_fires():
    """
    Load all historical fire data from local CSV files into memory.

    Loads MODIS or VIIRS data for 2016-2024 covering Indonesia and Malaysia.
    Singapore data is excluded as it has negligible fire detections.
    Data source is configured via FIRE_DATA_SOURCE environment variable.

    Returns:
        pandas.DataFrame: All fire detections with columns:
            latitude, longitude, frp, acq_date, acq_time, acq_datetime, satellite
    """
    global _FIRE_DATA_CACHE

    # Return cached data if already loaded
    if _FIRE_DATA_CACHE is not None:
        return _FIRE_DATA_CACHE

    print(f"Loading historical fire data from {FIRE_DATA_SOURCE}...")

    # Find all CSV files
    csv_files = sorted(FIRE_DATA_DIR.glob("*.csv"))

    # Filter to only Indonesia and Malaysia (exclude Singapore)
    indonesia_files = [f for f in csv_files if 'Indonesia' in f.name]
    malaysia_files = [f for f in csv_files if 'Malaysia' in f.name]

    all_files = indonesia_files + malaysia_files

    if len(all_files) == 0:
        print(f"WARNING: No fire CSV files found in {FIRE_DATA_DIR}")
        return pd.DataFrame()

    print(f"Found {len(all_files)} CSV files (Indonesia + Malaysia)")

    # Load all CSV files
    dataframes = []
    total_records = 0

    for csv_file in all_files:
        df = pd.read_csv(csv_file)

        # Standardize column names to match expected format
        # VIIRS uses 'bright_ti4', MODIS uses 'brightness'
        df = df.rename(columns={
            'bright_ti4': 'brightness',
        })

        # Parse acquisition datetime
        df['acq_datetime'] = pd.to_datetime(
            df['acq_date'] + ' ' + df['acq_time'].astype(str).str.zfill(4),
            format='%Y-%m-%d %H%M'
        )

        dataframes.append(df)
        total_records += len(df)

    # Combine all data
    all_fires = pd.concat(dataframes, ignore_index=True)

    print(f"Loaded {total_records:,} fire records from 2016-2024")
    print(f"Data source: {FIRE_DATA_SOURCE}")
    print(f"Memory usage: ~{all_fires.memory_usage(deep=True).sum() / (1024**2):.1f} MB")

    # Cache for future use
    _FIRE_DATA_CACHE = all_fires

    return all_fires


def get_fires_for_date(target_date):
    """
    Get fire detections for a specific date.

    Args:
        target_date: Date string (YYYY-MM-DD) or pandas.Timestamp

    Returns:
        pandas.DataFrame: Fire detections for that date with columns:
            latitude, longitude, frp, acq_datetime
    """
    # Load all data (uses cache if already loaded)
    all_fires = load_all_historical_fires()

    if len(all_fires) == 0:
        return pd.DataFrame(columns=['latitude', 'longitude', 'frp', 'acq_datetime'])

    # Convert target_date to string if needed
    if isinstance(target_date, pd.Timestamp):
        target_date = target_date.strftime('%Y-%m-%d')

    # Filter by date
    fires_for_date = all_fires[all_fires['acq_date'] == target_date].copy()

    # Return only needed columns
    return fires_for_date[['latitude', 'longitude', 'frp', 'acq_datetime']]


def get_fires_for_date_range(start_date, end_date):
    """
    Get fire detections for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        pandas.DataFrame: Fire detections in date range
    """
    # Load all data (uses cache if already loaded)
    all_fires = load_all_historical_fires()

    if len(all_fires) == 0:
        return pd.DataFrame(columns=['latitude', 'longitude', 'frp', 'acq_datetime'])

    # Convert to strings if needed
    if isinstance(start_date, pd.Timestamp):
        start_date = start_date.strftime('%Y-%m-%d')
    if isinstance(end_date, pd.Timestamp):
        end_date = end_date.strftime('%Y-%m-%d')

    # Filter by date range
    fires_in_range = all_fires[
        (all_fires['acq_date'] >= start_date) &
        (all_fires['acq_date'] <= end_date)
    ].copy()

    # Return only needed columns
    return fires_in_range[['latitude', 'longitude', 'frp', 'acq_datetime']]


def clear_cache():
    """
    Clear the fire data cache.
    Useful for freeing memory after training is complete.
    """
    global _FIRE_DATA_CACHE
    _FIRE_DATA_CACHE = None
    print("Fire data cache cleared")
