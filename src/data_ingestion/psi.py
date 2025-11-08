"""
Singapore PSI (Pollutant Standards Index) data ingestion.
Fetches current and historical PSI data from Singapore NEA via data.gov.sg API.
"""

import pandas as pd
import requests
from datetime import datetime
from sqlalchemy.exc import IntegrityError


# Singapore PSI API Configuration
CURRENT_PSI_URL = "https://api.data.gov.sg/v1/environment/psi"
HISTORICAL_PSI_URL = "https://data.gov.sg/api/action/datastore_search"
HISTORICAL_DATASET_ID = "d_b4cf557f8750260d229c49fd768e11ed"


def get_psi_status(psi_value):
    """
    Return PSI status band based on value.

    Args:
        psi_value: PSI value (0-500+)

    Returns:
        str: Status category
    """
    if psi_value <= 50:
        return "Good"
    elif psi_value <= 100:
        return "Moderate"
    elif psi_value <= 200:
        return "Unhealthy"
    elif psi_value <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def parse_psi_response(data):
    """
    Parse PSI API response into DataFrame.

    Args:
        data: JSON response from PSI API

    Returns:
        pandas.DataFrame: PSI readings by region
    """
    if 'items' not in data or len(data['items']) == 0:
        return pd.DataFrame()

    item = data['items'][0]
    timestamp = pd.to_datetime(item['timestamp'])
    readings = item['readings']

    records = []

    # Parse PSI 24-hour readings
    if 'psi_twenty_four_hourly' in readings:
        psi_24h = readings['psi_twenty_four_hourly']

        for region, psi_value in psi_24h.items():
            record = {
                'timestamp': timestamp,
                'region': region,
                'psi_24h': psi_value
            }

            # Add PM2.5 if available
            if 'pm25_twenty_four_hourly' in readings:
                record['pm25_24h'] = readings['pm25_twenty_four_hourly'].get(region)

            # Add PM10 if available
            if 'pm10_twenty_four_hourly' in readings:
                record['pm10_24h'] = readings['pm10_twenty_four_hourly'].get(region)

            # Add O3 sub-index if available
            if 'o3_sub_index' in readings:
                record['o3_sub_index'] = readings['o3_sub_index'].get(region)

            # Add CO sub-index if available
            if 'co_sub_index' in readings:
                record['co_sub_index'] = readings['co_sub_index'].get(region)

            # Add NO2 if available
            if 'no2_one_hour_max' in readings:
                record['no2_1h_max'] = readings['no2_one_hour_max'].get(region)

            # Add SO2 if available
            if 'so2_twenty_four_hourly' in readings:
                record['so2_24h'] = readings['so2_twenty_four_hourly'].get(region)

            records.append(record)

    return pd.DataFrame(records)


def fetch_current_psi():
    """
    Fetch current PSI readings from Singapore NEA.

    Returns:
        pandas.DataFrame: Current PSI readings for all regions
    """
    try:
        response = requests.get(CURRENT_PSI_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        return parse_psi_response(data)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching current PSI: {e}")
        return pd.DataFrame()


def fetch_historical_psi(limit=100, offset=0):
    """
    Fetch historical PSI data from data.gov.sg archive.

    Args:
        limit: Number of records to fetch (max 100 per request)
        offset: Offset for pagination

    Returns:
        pandas.DataFrame: Historical PSI readings
    """
    params = {
        'resource_id': HISTORICAL_DATASET_ID,
        'limit': min(limit, 100),
        'offset': offset
    }

    try:
        response = requests.get(HISTORICAL_PSI_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get('success') or 'result' not in data:
            return pd.DataFrame()

        records = data['result'].get('records', [])

        if len(records) == 0:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(records)

        # Parse timestamp
        if '24hr_psi' in df.columns:
            df = df.rename(columns={'24hr_psi': 'timestamp'})

        # Parse timestamp column
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Reshape from wide to long format (one row per region)
        region_columns = ['north', 'south', 'east', 'west', 'central']
        id_vars = ['timestamp']

        if 'national' in df.columns:
            region_columns.append('national')

        # Melt to long format
        df_long = df.melt(
            id_vars=id_vars,
            value_vars=region_columns,
            var_name='region',
            value_name='psi_24h'
        )

        # Convert PSI to numeric
        df_long['psi_24h'] = pd.to_numeric(df_long['psi_24h'], errors='coerce')

        # Drop null values
        df_long = df_long.dropna(subset=['psi_24h'])

        return df_long

    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical PSI: {e}")
        return pd.DataFrame()


def save_psi_to_db(df):
    """
    Save PSI readings to database.

    Args:
        df: DataFrame of PSI readings

    Returns:
        int: Number of records saved
    """
    from src.database import get_session, PSIReading

    if len(df) == 0:
        return 0

    session = get_session()
    count = 0

    try:
        for _, row in df.iterrows():
            psi = PSIReading(
                timestamp=row['timestamp'],
                region=row['region'],
                psi_24h=int(row['psi_24h']) if pd.notna(row['psi_24h']) else None,
                pm25_24h=int(row['pm25_24h']) if 'pm25_24h' in row and pd.notna(row['pm25_24h']) else None,
                pm10_24h=int(row['pm10_24h']) if 'pm10_24h' in row and pd.notna(row['pm10_24h']) else None,
                o3_sub_index=int(row['o3_sub_index']) if 'o3_sub_index' in row and pd.notna(row['o3_sub_index']) else None,
                co_sub_index=int(row['co_sub_index']) if 'co_sub_index' in row and pd.notna(row['co_sub_index']) else None,
                no2_1h_max=int(row['no2_1h_max']) if 'no2_1h_max' in row and pd.notna(row['no2_1h_max']) else None,
                so2_24h=int(row['so2_24h']) if 'so2_24h' in row and pd.notna(row['so2_24h']) else None
            )

            try:
                session.add(psi)
                session.commit()
                count += 1
            except IntegrityError:
                # Duplicate record (unique constraint on timestamp+region)
                session.rollback()
                continue

    except Exception as e:
        print(f"Error saving PSI to database: {e}")
        session.rollback()
    finally:
        session.close()

    return count
