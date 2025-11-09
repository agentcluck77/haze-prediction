"""
Historical data fetching for training.
Fetches PSI, fire, and weather data from archives.
"""

import pandas as pd
from datetime import datetime, timedelta
from src.data_ingestion.psi import fetch_historical_psi
from src.data_ingestion.weather import fetch_historical_weather


def fetch_historical_psi_range(start_date, end_date):
    """
    Fetch historical PSI data for a specific date range from local CSV file.

    Uses local Historical24hrPSI.csv file stored in data/PSI/
    Coverage: Jan 2014 to present.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        pandas.DataFrame: PSI readings in date range
    """
    from src.training.psi_data_loader import get_psi_for_date_range

    print(f"Loading PSI data for {start_date} to {end_date} from local CSV...")

    try:
        result = get_psi_for_date_range(start_date, end_date)
        print(f"Loaded {len(result)} PSI records from local file")
        return result

    except Exception as e:
        print(f"Error loading PSI data: {e}")
        return pd.DataFrame()


def fetch_historical_fires_for_date(date_str):
    """
    Fetch historical fire data for a specific date from local CSV files.

    Uses VIIRS SNPP historical data stored locally in data/FIRMS_historical/
    Covers Feb 2016 - Dec 2024 for Indonesia and Malaysia only.

    Args:
        date_str: Date (YYYY-MM-DD)

    Returns:
        pandas.DataFrame: Fire detections for the date with columns:
            latitude, longitude, frp, acq_datetime
    """
    from src.training.fire_data_loader import get_fires_for_date

    try:
        df = get_fires_for_date(date_str)
        return df

    except Exception as e:
        print(f"Error loading fire data for {date_str}: {e}")
        return pd.DataFrame(columns=['latitude', 'longitude', 'frp', 'acq_datetime'])


def fetch_historical_weather_batch(latitude, longitude, start_date, end_date):
    """
    Fetch historical weather data from ERA5 archive.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        pandas.DataFrame: Historical hourly weather data
    """
    return fetch_historical_weather(latitude, longitude, start_date, end_date)
