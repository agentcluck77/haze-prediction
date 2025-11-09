"""
Open-Meteo weather data ingestion.
Fetches current weather, forecasts, and historical data from Open-Meteo API.
"""

import pandas as pd
import requests
from datetime import datetime
from sqlalchemy.exc import IntegrityError


# Open-Meteo API Configuration
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/era5"

# Weather parameters
WEATHER_PARAMS = [
    'temperature_2m',
    'relative_humidity_2m',
    'wind_speed_10m',
    'wind_direction_10m',
    'wind_gusts_10m',
    'pressure_msl'
]


def fetch_current_weather(latitude, longitude):
    """
    Fetch current weather conditions from Open-Meteo.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        pandas.DataFrame: Current weather with columns:
            timestamp, temperature_2m, relative_humidity_2m,
            wind_speed_10m, wind_direction_10m, pressure_msl
    """
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'current': ','.join(WEATHER_PARAMS),
        'timezone': 'Asia/Singapore'
    }

    try:
        response = requests.get(FORECAST_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'current' not in data:
            return pd.DataFrame()

        current = data['current']

        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': pd.to_datetime(current['time']),
            'temperature_2m': current.get('temperature_2m'),
            'relative_humidity_2m': current.get('relative_humidity_2m'),
            'wind_speed_10m': current.get('wind_speed_10m'),
            'wind_direction_10m': current.get('wind_direction_10m'),
            'wind_gusts_10m': current.get('wind_gusts_10m'),
            'pressure_msl': current.get('pressure_msl')
        }])

        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching current weather: {e}")
        return pd.DataFrame()


def fetch_weather_forecast(latitude, longitude, hours=24):
    """
    Fetch hourly weather forecast from Open-Meteo.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        hours: Number of hours to forecast (default: 24)

    Returns:
        pandas.DataFrame: Hourly forecast data
    """
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'hourly': ','.join(WEATHER_PARAMS),
        'timezone': 'Asia/Singapore',
        'forecast_days': max(1, (hours // 24) + 1)
    }

    try:
        response = requests.get(FORECAST_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'hourly' not in data:
            return pd.DataFrame()

        hourly = data['hourly']

        # Convert to DataFrame
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(hourly['time']),
            'temperature_2m': hourly.get('temperature_2m'),
            'relative_humidity_2m': hourly.get('relative_humidity_2m'),
            'wind_speed_10m': hourly.get('wind_speed_10m'),
            'wind_direction_10m': hourly.get('wind_direction_10m'),
            'wind_gusts_10m': hourly.get('wind_gusts_10m'),
            'pressure_msl': hourly.get('pressure_msl')
        })

        # Limit to requested hours
        df = df.head(hours)

        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather forecast: {e}")
        return pd.DataFrame()


def fetch_weather_multiple_locations(locations, hours=24):
    """
    Fetch weather forecast for multiple locations.

    Args:
        locations: List of dicts with keys: name, lat, lon
        hours: Number of hours to forecast

    Returns:
        pandas.DataFrame: Combined forecast data with location column
    """
    all_data = []

    for loc in locations:
        df = fetch_weather_forecast(loc['lat'], loc['lon'], hours)

        if len(df) > 0:
            df['location'] = loc['name']
            df['latitude'] = loc['lat']
            df['longitude'] = loc['lon']
            all_data.append(df)

    if len(all_data) == 0:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


def fetch_historical_weather(latitude, longitude, start_date, end_date):
    """
    Fetch historical weather data from ERA5 archive.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        pandas.DataFrame: Historical hourly weather data

    Raises:
        requests.exceptions.HTTPError: For rate limiting (429) and other HTTP errors
    """
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'start_date': start_date,
        'end_date': end_date,
        'hourly': 'temperature_2m,wind_speed_10m,wind_direction_10m,pressure_msl,relative_humidity_2m',
        'timezone': 'Asia/Singapore'
    }

    try:
        response = requests.get(ARCHIVE_URL, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        if 'hourly' not in data:
            return pd.DataFrame()

        hourly = data['hourly']

        # Convert to DataFrame
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(hourly['time']),
            'temperature_2m': hourly.get('temperature_2m'),
            'relative_humidity_2m': hourly.get('relative_humidity_2m'),
            'wind_speed_10m': hourly.get('wind_speed_10m'),
            'wind_direction_10m': hourly.get('wind_direction_10m'),
            'pressure_msl': hourly.get('pressure_msl')
        })

        return df

    except requests.exceptions.HTTPError as e:
        # Re-raise HTTP errors (including 429 rate limits) for retry logic
        raise
    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical weather: {e}")
        return pd.DataFrame()


def save_weather_to_db(df):
    """
    Save weather data to database.

    Args:
        df: DataFrame of weather data

    Returns:
        int: Number of records saved
    """
    from src.database import get_session, WeatherData

    if len(df) == 0:
        return 0

    session = get_session()
    count = 0

    try:
        for _, row in df.iterrows():
            weather = WeatherData(
                location=row.get('location', 'Unknown'),
                latitude=row.get('latitude'),
                longitude=row.get('longitude'),
                timestamp=row['timestamp'],
                temperature_2m=row.get('temperature_2m'),
                relative_humidity_2m=row.get('relative_humidity_2m'),
                wind_speed_10m=row.get('wind_speed_10m'),
                wind_direction_10m=row.get('wind_direction_10m'),
                wind_gusts_10m=row.get('wind_gusts_10m'),
                pressure_msl=row.get('pressure_msl'),
                is_forecast=row.get('is_forecast', False)
            )

            try:
                session.add(weather)
                session.commit()
                count += 1
            except IntegrityError:
                # Duplicate record, skip
                session.rollback()
                continue

    except Exception as e:
        print(f"Error saving weather to database: {e}")
        session.rollback()
    finally:
        session.close()

    return count
