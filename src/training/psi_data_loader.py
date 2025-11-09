"""
Historical PSI data loader from local CSV file.
Loads all PSI data into memory for fast lookups during training.
"""

import pandas as pd
from pathlib import Path


# Path to historical PSI data
PSI_DATA_FILE = Path(__file__).parent.parent.parent / "data" / "PSI" / "Historical24hrPSI.csv"

# Global cache for PSI data (loaded once)
_PSI_DATA_CACHE = None


def load_all_historical_psi():
    """
    Load all historical PSI data from local CSV file into memory.

    Returns:
        pandas.DataFrame: All PSI readings with columns:
            timestamp, region, psi_24h
    """
    global _PSI_DATA_CACHE

    # Return cached data if already loaded
    if _PSI_DATA_CACHE is not None:
        return _PSI_DATA_CACHE

    print(f"Loading historical PSI data from {PSI_DATA_FILE.name}...")

    if not PSI_DATA_FILE.exists():
        print(f"ERROR: PSI data file not found: {PSI_DATA_FILE}")
        return pd.DataFrame()

    # Load CSV
    df = pd.read_csv(PSI_DATA_FILE)

    # Parse timestamp (mixed formats: D/M/YYYY H:MM and ISO8601)
    df['timestamp'] = pd.to_datetime(df['24hr_psi'], format='mixed', dayfirst=True)

    # Melt regional columns into long format
    regional_data = []

    for region in ['north', 'south', 'east', 'west', 'central']:
        region_df = df[['timestamp', region]].copy()
        region_df = region_df.rename(columns={region: 'psi_24h'})
        region_df['region'] = region
        regional_data.append(region_df)

    # Combine all regional data
    all_psi = pd.concat(regional_data, ignore_index=True)

    # Compute national average
    national_avg = all_psi.groupby('timestamp').agg({'psi_24h': 'mean'}).reset_index()
    national_avg['region'] = 'national'
    national_avg = national_avg.rename(columns={'psi_24h': 'psi_24h'})

    # Add national to all_psi
    all_psi = pd.concat([all_psi, national_avg], ignore_index=True)

    # Sort by timestamp
    all_psi = all_psi.sort_values('timestamp').reset_index(drop=True)

    print(f"Loaded {len(all_psi):,} PSI records")
    print(f"Date range: {all_psi['timestamp'].min()} to {all_psi['timestamp'].max()}")
    print(f"Regions: {sorted(all_psi['region'].unique())}")
    print(f"Memory usage: ~{all_psi.memory_usage(deep=True).sum() / (1024**2):.1f} MB")

    # Cache for future use
    _PSI_DATA_CACHE = all_psi

    return all_psi


def get_psi_for_date_range(start_date, end_date):
    """
    Get PSI readings for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        pandas.DataFrame: PSI readings in date range with columns:
            timestamp, region, psi_24h
    """
    # Load all data (uses cache if already loaded)
    all_psi = load_all_historical_psi()

    if len(all_psi) == 0:
        return pd.DataFrame()

    # Convert to datetime if needed
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    # Add one day to end_date to be inclusive
    end_dt = end_dt + pd.Timedelta(days=1)

    # Filter by date range
    psi_in_range = all_psi[
        (all_psi['timestamp'] >= start_dt) &
        (all_psi['timestamp'] < end_dt)
    ].copy()

    return psi_in_range


def clear_cache():
    """
    Clear the PSI data cache.
    Useful for freeing memory after training is complete.
    """
    global _PSI_DATA_CACHE
    _PSI_DATA_CACHE = None
    print("PSI data cache cleared")
