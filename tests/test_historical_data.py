"""
Test historical data fetching and preparation for training.
Following TDD protocol: Write tests first, then implement.
"""

import pytest
import pandas as pd
from datetime import datetime


class TestHistoricalDataFetching:
    """Test suite for historical data fetching."""

    def test_fetch_historical_psi_batch(self):
        """Test fetching large batch of historical PSI data."""
        from src.training.historical_data import fetch_historical_psi_batch

        # Fetch 1000 records
        df = fetch_historical_psi_batch(limit=1000)

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        assert len(df) > 0, "Should have historical PSI data"
        assert 'timestamp' in df.columns, "Should have timestamp"
        assert 'region' in df.columns, "Should have region"
        assert 'psi_24h' in df.columns, "Should have PSI values"

    def test_fetch_historical_psi_date_range(self):
        """Test fetching PSI for specific date range."""
        from src.training.historical_data import fetch_historical_psi_range

        df = fetch_historical_psi_range(
            start_date="2024-01-01",
            end_date="2024-01-07"
        )

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        if len(df) > 0:
            assert df['timestamp'].min() >= pd.Timestamp("2024-01-01")
            assert df['timestamp'].max() <= pd.Timestamp("2024-01-08")

    def test_fetch_historical_fires_for_date(self):
        """Test fetching historical fire data for a specific date."""
        from src.training.historical_data import fetch_historical_fires_for_date

        df = fetch_historical_fires_for_date("2024-06-15")

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        # Fires may not exist for every date, so just check structure
        assert 'latitude' in df.columns or len(df) == 0
        assert 'longitude' in df.columns or len(df) == 0

    def test_fetch_historical_weather_batch(self):
        """Test fetching historical weather data."""
        from src.training.historical_data import fetch_historical_weather_batch

        df = fetch_historical_weather_batch(
            latitude=1.3521,
            longitude=103.8198,
            start_date="2024-01-01",
            end_date="2024-01-03"
        )

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"
        assert len(df) > 0, "Should have weather data"
        assert 'timestamp' in df.columns
        assert 'wind_speed_10m' in df.columns
        assert 'wind_direction_10m' in df.columns


class TestTrainingDataPreparation:
    """Test suite for training data preparation."""

    def test_align_datasets_on_timestamp(self):
        """Test aligning PSI, fire, and weather data on timestamps."""
        from src.training.data_preparation import align_datasets

        # Mock data
        psi_df = pd.DataFrame([{
            'timestamp': pd.Timestamp('2024-01-01 12:00:00'),
            'region': 'national',
            'psi_24h': 50
        }])

        fire_df = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 100,
            'acq_datetime': pd.Timestamp('2024-01-01 11:00:00')
        }])

        weather_df = pd.DataFrame([{
            'timestamp': pd.Timestamp('2024-01-01 12:00:00'),
            'wind_speed_10m': 10.0,
            'wind_direction_10m': 180.0
        }])

        aligned_df = align_datasets(psi_df, fire_df, weather_df)

        assert isinstance(aligned_df, pd.DataFrame), "Should return DataFrame"
        assert 'timestamp' in aligned_df.columns
        assert len(aligned_df) > 0, "Should have aligned records"

    def test_engineer_features_for_training(self):
        """Test feature engineering for a single timestamp."""
        from src.training.data_preparation import engineer_features_for_timestamp

        timestamp = pd.Timestamp('2024-01-01 12:00:00')

        # Mock minimal data
        fires = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 100,
            'acq_datetime': timestamp - pd.Timedelta(hours=1)
        }])

        weather = pd.DataFrame([{
            'timestamp': timestamp + pd.Timedelta(hours=i),
            'wind_speed_10m': 10.0,
            'wind_direction_10m': 180.0
        } for i in range(24)])

        current_psi = 50

        features = engineer_features_for_timestamp(
            timestamp, fires, weather, current_psi
        )

        assert isinstance(features, dict), "Should return dict of features"
        assert 'fire_risk_score' in features
        assert 'wind_transport_score' in features
        assert 'baseline_score' in features
        assert 0 <= features['fire_risk_score'] <= 100
        assert 0 <= features['wind_transport_score'] <= 100
        assert 0 <= features['baseline_score'] <= 100

    def test_create_target_variables(self):
        """Test creating target PSI values at future horizons."""
        from src.training.data_preparation import create_target_variables

        # Mock PSI data spanning multiple days
        psi_df = pd.DataFrame([{
            'timestamp': pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i),
            'region': 'national',
            'psi_24h': 50 + i
        } for i in range(200)])

        targets = create_target_variables(
            psi_df,
            base_timestamp=pd.Timestamp('2024-01-01 12:00:00'),
            region='national'
        )

        assert isinstance(targets, dict), "Should return dict of targets"
        assert 'psi_24h_ahead' in targets
        assert 'psi_48h_ahead' in targets
        assert 'psi_72h_ahead' in targets
        assert 'psi_7d_ahead' in targets

    def test_prepare_full_training_dataset(self):
        """Test preparing complete training dataset."""
        from src.training.data_preparation import prepare_training_dataset

        # This will use real data or sample data
        df = prepare_training_dataset(
            start_date="2024-01-01",
            end_date="2024-01-07",
            sample_hours=24  # Sample every 24h to reduce test time
        )

        assert isinstance(df, pd.DataFrame), "Should return DataFrame"

        # If no data available for this date range, test passes
        # (historical data may not be available for all dates)
        if len(df) == 0:
            pytest.skip("No historical data available for this date range")

        # Check feature columns
        required_columns = [
            'timestamp',
            'fire_risk_score',
            'wind_transport_score',
            'baseline_score',
            'psi_24h_ahead',
            'psi_48h_ahead',
            'psi_72h_ahead',
            'psi_7d_ahead'
        ]

        for col in required_columns:
            assert col in df.columns, f"Should have {col} column"

        # Check no nulls in features
        if len(df) > 0:
            assert df['fire_risk_score'].notna().all(), "Fire risk should not have nulls"
            assert df['wind_transport_score'].notna().all(), "Wind transport should not have nulls"
            assert df['baseline_score'].notna().all(), "Baseline should not have nulls"
