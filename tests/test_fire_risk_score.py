"""
Test fire risk score calculation algorithm.
Following TDD protocol: Write tests first, then implement.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import numpy as np


class TestFireRiskScore:
    """Test suite for fire risk score calculation."""

    def test_calculate_fire_risk_score_no_fires(self):
        """Test that empty DataFrame returns risk score of 0."""
        from src.features.fire_risk import calculate_fire_risk_score

        empty_df = pd.DataFrame(columns=['latitude', 'longitude', 'frp', 'acq_datetime'])
        score = calculate_fire_risk_score(empty_df)

        assert score == 0, "No fires should give risk score of 0"

    def test_calculate_fire_risk_score_single_fire(self):
        """Test risk score with a single fire."""
        from src.features.fire_risk import calculate_fire_risk_score

        # Single fire in Sumatra (close to Singapore)
        fires_df = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 100.0,  # MW
            'acq_datetime': datetime.now() - timedelta(hours=1)
        }])

        score = calculate_fire_risk_score(fires_df)

        assert 0 < score <= 100, f"Risk score should be 0-100, got {score}"
        assert score > 3, "Close, recent fire with high FRP should have meaningful score"

    def test_calculate_fire_risk_score_range(self):
        """Test that risk score is always in 0-100 range."""
        from src.features.fire_risk import calculate_fire_risk_score

        # Many intense fires
        fires_df = pd.DataFrame([{
            'latitude': 1.0 + i*0.1,
            'longitude': 103.0 + i*0.1,
            'frp': 500.0,  # Very high FRP
            'acq_datetime': datetime.now()
        } for i in range(100)])

        score = calculate_fire_risk_score(fires_df)

        assert 0 <= score <= 100, f"Risk score should be capped at 100, got {score}"

    def test_fire_risk_decreases_with_distance(self):
        """Test that fires farther away contribute less to risk."""
        from src.features.fire_risk import calculate_fire_risk_score

        # Close fire
        close_fire = pd.DataFrame([{
            'latitude': 1.5,
            'longitude': 103.5,
            'frp': 100.0,
            'acq_datetime': datetime.now()
        }])

        # Far fire (same FRP, same time, but far away)
        far_fire = pd.DataFrame([{
            'latitude': -5.0,
            'longitude': 110.0,
            'frp': 100.0,
            'acq_datetime': datetime.now()
        }])

        close_score = calculate_fire_risk_score(close_fire)
        far_score = calculate_fire_risk_score(far_fire)

        assert close_score > far_score, "Closer fire should have higher risk score"

    def test_fire_risk_decreases_with_age(self):
        """Test that older fires contribute less to risk."""
        from src.features.fire_risk import calculate_fire_risk_score

        # Recent fire
        recent_fire = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 100.0,
            'acq_datetime': datetime.now() - timedelta(hours=1)
        }])

        # Old fire (same location, same FRP, but 48h old)
        old_fire = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 100.0,
            'acq_datetime': datetime.now() - timedelta(hours=48)
        }])

        recent_score = calculate_fire_risk_score(recent_fire)
        old_score = calculate_fire_risk_score(old_fire)

        assert recent_score > old_score, "Recent fire should have higher risk score"

    def test_fire_risk_increases_with_frp(self):
        """Test that higher FRP fires have higher risk."""
        from src.features.fire_risk import calculate_fire_risk_score

        # Low intensity
        low_fire = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 50.0,
            'acq_datetime': datetime.now()
        }])

        # High intensity
        high_fire = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 300.0,
            'acq_datetime': datetime.now()
        }])

        low_score = calculate_fire_risk_score(low_fire)
        high_score = calculate_fire_risk_score(high_fire)

        assert high_score > low_score, "Higher FRP should give higher risk score"

    def test_fire_risk_with_custom_singapore_coords(self):
        """Test that custom Singapore coordinates work."""
        from src.features.fire_risk import calculate_fire_risk_score

        fires_df = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 100.0,
            'acq_datetime': datetime.now()
        }])

        # Use different Singapore coords
        score = calculate_fire_risk_score(fires_df, singapore_coords=(1.4, 103.9))

        assert 0 < score <= 100, "Should work with custom coordinates"

    def test_fire_risk_multiple_fires_aggregate(self):
        """Test that multiple fires aggregate correctly."""
        from src.features.fire_risk import calculate_fire_risk_score

        # Single fire
        single = pd.DataFrame([{
            'latitude': 1.0,
            'longitude': 103.0,
            'frp': 100.0,
            'acq_datetime': datetime.now()
        }])

        # Multiple similar fires
        multiple = pd.DataFrame([{
            'latitude': 1.0 + i*0.01,
            'longitude': 103.0 + i*0.01,
            'frp': 100.0,
            'acq_datetime': datetime.now()
        } for i in range(10)])

        single_score = calculate_fire_risk_score(single)
        multiple_score = calculate_fire_risk_score(multiple)

        assert multiple_score > single_score, "Multiple fires should have higher total risk"
