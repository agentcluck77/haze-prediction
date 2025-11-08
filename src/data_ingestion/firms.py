"""
FIRMS (Fire Information for Resource Management System) data ingestion.
Fetches fire detection data from NASA FIRMS API.
"""

import os
import pandas as pd
import requests
from datetime import datetime
from sqlalchemy.exc import IntegrityError


# FIRMS API Configuration
MAP_KEY = os.getenv('FIRMS_MAP_KEY', 'f6cd6de4fa5a42514a72c8525064e890')
BASE_URL = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv'
DEFAULT_BBOX = "95,-11,141,6"  # Indonesia


def fetch_recent_fires(days=1, bbox=None, satellite='VIIRS_SNPP_NRT'):
    """
    Fetch recent fire detections from FIRMS API.

    Args:
        days: Number of days to fetch (1-10)
        bbox: Bounding box as "west,south,east,north" (default: Indonesia)
        satellite: Satellite dataset (default: VIIRS_SNPP_NRT - matches historical data)

    Returns:
        pandas.DataFrame: Fire detections with columns:
            latitude, longitude, frp, brightness, confidence,
            acq_date, acq_time, satellite
    """
    if bbox is None:
        bbox = DEFAULT_BBOX

    url = f"{BASE_URL}/{MAP_KEY}/{satellite}/{bbox}/{days}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse CSV response
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))

        # Return empty DataFrame if no fires
        if len(df) == 0:
            return pd.DataFrame(columns=[
                'latitude', 'longitude', 'frp', 'brightness',
                'confidence', 'acq_date', 'acq_time', 'satellite'
            ])

        # Standardize column names
        df = df.rename(columns={
            'lat': 'latitude',
            'lon': 'longitude',
            'bright_ti4': 'brightness',
            'confidence': 'confidence',
        })

        # Add satellite name if not present
        if 'satellite' not in df.columns:
            df['satellite'] = satellite

        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching FIRMS data: {e}")
        return pd.DataFrame(columns=[
            'latitude', 'longitude', 'frp', 'brightness',
            'confidence', 'acq_date', 'acq_time', 'satellite'
        ])


def parse_acquisition_datetime(acq_date, acq_time):
    """
    Parse FIRMS acquisition date and time into Python datetime.

    Args:
        acq_date: Date string (YYYY-MM-DD)
        acq_time: Time string (HHMM)

    Returns:
        datetime: Combined datetime object
    """
    try:
        # Pad time to 4 digits if needed
        time_str = str(acq_time).zfill(4)
        hour = int(time_str[:2])
        minute = int(time_str[2:4])

        # Parse date
        date_obj = datetime.strptime(acq_date, '%Y-%m-%d')

        # Combine
        return datetime(
            date_obj.year, date_obj.month, date_obj.day,
            hour, minute
        )
    except (ValueError, TypeError) as e:
        print(f"Error parsing datetime: {acq_date} {acq_time} - {e}")
        return None


def deduplicate_fires(df):
    """
    Remove duplicate fire detections.

    Duplicates are defined as same latitude, longitude, date, time, and satellite.

    Args:
        df: DataFrame of fire detections

    Returns:
        DataFrame: Deduplicated fire detections
    """
    if len(df) == 0:
        return df

    return df.drop_duplicates(
        subset=['latitude', 'longitude', 'acq_date', 'acq_time', 'satellite'],
        keep='first'
    )


def save_fires_to_db(df):
    """
    Save fire detections to database.

    Args:
        df: DataFrame of fire detections

    Returns:
        int: Number of records saved
    """
    from src.database import get_session, FireDetection

    if len(df) == 0:
        return 0

    session = get_session()
    count = 0

    try:
        for _, row in df.iterrows():
            # Parse acquisition datetime
            acq_datetime = parse_acquisition_datetime(
                row['acq_date'],
                row['acq_time']
            )

            if acq_datetime is None:
                continue

            # Create record
            fire = FireDetection(
                timestamp=acq_datetime,
                latitude=row['latitude'],
                longitude=row['longitude'],
                frp=row.get('frp'),
                brightness=row.get('brightness'),
                confidence=str(row.get('confidence', '')),
                acq_date=acq_datetime.date(),
                acq_time=row['acq_time'],
                satellite=row.get('satellite', '')
            )

            try:
                session.add(fire)
                session.commit()
                count += 1
            except IntegrityError:
                # Duplicate record, skip
                session.rollback()
                continue

    except Exception as e:
        print(f"Error saving fires to database: {e}")
        session.rollback()
    finally:
        session.close()

    return count
