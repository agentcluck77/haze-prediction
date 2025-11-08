"""
Test Open-Meteo weather data ingestion module.
Following TDD protocol: Write tests first, then implement.
"""

import pytest
from datetime import datetime
import pandas as pd


class TestWeatherIngestion:
    """Test suite for Open-Meteo weather data ingestion."""

    def test_fetch_current_weather_returns_dataframe(self):
        """Test that fetch_current_weather returns a pandas DataFrame."""
        from src.data_ingestion.weather import fetch_current_weather

        df = fetch_current_weather(latitude=1.3521, longitude=103.8198)
        assert isinstance(df, pd.DataFrame), "Should return a DataFrame"
        assert len(df) > 0, "Should have at least one record"

    def test_fetch_current_weather_has_required_columns(self):
        """Test that DataFrame has all required columns."""
        from src.data_ingestion.weather import fetch_current_weather

        df = fetch_current_weather(latitude=1.3521, longitude=103.8198)

        required_columns = [
            'timestamp', 'temperature_2m', 'relative_humidity_2m',
            'wind_speed_10m', 'wind_direction_10m', 'pressure_msl'
        ]

        for col in required_columns:
            assert col in df.columns, f"Column {col} should exist"

    def test_fetch_weather_forecast_returns_dataframe(self):
        """Test fetching hourly weather forecast."""
        from src.data_ingestion.weather import fetch_weather_forecast

        df = fetch_weather_forecast(
            latitude=1.3521,
            longitude=103.8198,
            hours=24
        )

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        assert len(df) == 24, "Should return 24 hourly forecasts"

    def test_fetch_weather_forecast_has_wind_data(self):
        """Test that forecast includes wind data."""
        from src.data_ingestion.weather import fetch_weather_forecast

        df = fetch_weather_forecast(
            latitude=1.3521,
            longitude=103.8198,
            hours=48
        )

        assert 'wind_speed_10m' in df.columns
        assert 'wind_direction_10m' in df.columns
        assert df['wind_speed_10m'].notna().all(), "Wind speed should not have nulls"
        assert df['wind_direction_10m'].notna().all(), "Wind direction should not have nulls"

    def test_fetch_multiple_locations(self):
        """Test fetching weather for multiple locations."""
        from src.data_ingestion.weather import fetch_weather_multiple_locations

        locations = [
            {"name": "Singapore", "lat": 1.3521, "lon": 103.8198},
            {"name": "Riau", "lat": 0.5, "lon": 101.5},
        ]

        df = fetch_weather_multiple_locations(locations, hours=24)

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        assert 'location' in df.columns, "Should have location column"
        assert len(df['location'].unique()) == 2, "Should have 2 locations"

    def test_save_weather_to_database(self):
        """Test saving weather data to database."""
        from src.data_ingestion.weather import fetch_current_weather, save_weather_to_db
        from src.database import get_session, WeatherData

        # Fetch current weather
        df = fetch_current_weather(latitude=1.3521, longitude=103.8198)
        df['location'] = 'Singapore'
        df['latitude'] = 1.3521
        df['longitude'] = 103.8198
        df['is_forecast'] = False

        # Save to database
        count = save_weather_to_db(df)
        assert count > 0, "Should save at least one record"

        # Verify in database
        session = get_session()
        weather = session.query(WeatherData).limit(10).all()
        session.close()

        assert len(weather) > 0, "Should have weather records in database"

    def test_fetch_historical_weather_era5(self):
        """Test fetching historical weather from ERA5 archive."""
        from src.data_ingestion.weather import fetch_historical_weather

        df = fetch_historical_weather(
            latitude=1.3521,
            longitude=103.8198,
            start_date="2024-01-01",
            end_date="2024-01-03"
        )

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        assert len(df) > 0, "Should have historical data"
        assert 'timestamp' in df.columns
        assert 'wind_speed_10m' in df.columns
