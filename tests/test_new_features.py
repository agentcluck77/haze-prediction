"""
Test new feature engineering functions (PSI lags, temporal features, trends).
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.training.data_preparation import (
    engineer_psi_lag_features,
    engineer_temporal_features
)


def test_psi_lag_features():
    """Test PSI lag feature generation"""
    # Create sample PSI data for 2 days (48 hours)
    base_time = datetime(2024, 6, 15, 0, 0)
    timestamps = [base_time + timedelta(hours=i) for i in range(48)]
    psi_values = [50 + i * 2 for i in range(48)]  # PSI increasing from 50

    psi_df = pd.DataFrame({
        'timestamp': timestamps,
        'psi_24h': psi_values,
        'region': ['national'] * 48
    })

    # Test at hour 25 (next day at 1 AM) - should have all lags available
    test_time = datetime(2024, 6, 16, 1, 0)
    features = engineer_psi_lag_features(test_time, psi_df)

    # Check all lag features exist
    assert 'psi_lag_1h' in features
    assert 'psi_lag_6h' in features
    assert 'psi_lag_12h' in features
    assert 'psi_lag_24h' in features

    # Check values are correct (test_time is at hour 25)
    assert features['psi_lag_1h'] == 50 + 24*2  # 24 hours from start: 98
    assert features['psi_lag_6h'] == 50 + 19*2  # 19 hours from start: 88
    assert features['psi_lag_12h'] == 50 + 13*2  # 13 hours from start: 76
    assert features['psi_lag_24h'] == 50 + 1*2  # 1 hour from start: 52

    # Check trend features
    assert 'psi_trend_1h_6h' in features
    assert 'psi_trend_6h_24h' in features

    # Trend should be positive (PSI increasing)
    assert features['psi_trend_1h_6h'] == 98 - 88  # 10
    assert features['psi_trend_6h_24h'] == 88 - 52  # 36

    print("PSI lag features test passed!")


def test_psi_lag_features_missing_data():
    """Test PSI lag features with missing data"""
    # Create sparse PSI data
    psi_df = pd.DataFrame({
        'timestamp': [datetime(2024, 6, 15, 0, 0)],
        'psi_24h': [50],
        'region': ['national']
    })

    # Test at a time where lags are missing
    test_time = datetime(2024, 6, 15, 12, 0)
    features = engineer_psi_lag_features(test_time, psi_df)

    # Should use forward fill from the only available data point
    assert features['psi_lag_1h'] == 50  # Falls back to most recent past
    assert features['psi_lag_6h'] == 50
    assert features['psi_lag_12h'] == 50  # This exact time exists
    assert features['psi_lag_24h'] == 0.0  # No data before t=0

    print("PSI lag features with missing data test passed!")


def test_temporal_features():
    """Test temporal feature generation"""
    # Test during SW Monsoon (haze season)
    test_time_sw = datetime(2024, 9, 15, 14, 30)  # Sep 15, 2024, 2:30 PM, Sunday
    features_sw = engineer_temporal_features(test_time_sw)

    assert features_sw['hour'] == 14
    assert features_sw['day_of_week'] == 6  # Sunday
    assert features_sw['month'] == 9
    assert features_sw['season'] == 0  # SW Monsoon
    assert 'day_of_year' in features_sw

    # Test during NE Monsoon (wet season)
    test_time_ne = datetime(2024, 1, 10, 8, 0)  # Jan 10, 2024, 8:00 AM
    features_ne = engineer_temporal_features(test_time_ne)

    assert features_ne['hour'] == 8
    assert features_ne['month'] == 1
    assert features_ne['season'] == 1  # NE Monsoon

    # Test during Inter-monsoon
    test_time_inter = datetime(2024, 4, 15, 20, 0)  # Apr 15, 2024, 8:00 PM
    features_inter = engineer_temporal_features(test_time_inter)

    assert features_inter['month'] == 4
    assert features_inter['season'] == 2  # Inter-monsoon

    print("Temporal features test passed!")


def test_seasonal_classification():
    """Test that all months are correctly classified into seasons"""
    season_map = {
        1: 1, 2: 1, 3: 1,  # NE Monsoon
        4: 2, 5: 2,  # Inter-monsoon
        6: 0, 7: 0, 8: 0, 9: 0,  # SW Monsoon (haze season)
        10: 2, 11: 2,  # Inter-monsoon
        12: 1  # NE Monsoon
    }

    for month, expected_season in season_map.items():
        test_time = datetime(2024, month, 15, 12, 0)
        features = engineer_temporal_features(test_time)
        assert features['season'] == expected_season, f"Month {month} has wrong season"

    print("Seasonal classification test passed!")


if __name__ == '__main__':
    test_psi_lag_features()
    test_psi_lag_features_missing_data()
    test_temporal_features()
    test_seasonal_classification()
    print("\nAll tests passed!")
