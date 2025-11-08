"""
Test wind transport score calculation with trajectory simulation.
Following TDD protocol: Write tests first, then implement.
"""

import pytest
import pandas as pd
import numpy as np


class TestWindTransport:
    """Test suite for wind transport score calculation."""

    def test_calculate_wind_transport_score_no_fires(self):
        """Test that empty fire clusters return score of 0."""
        from src.features.wind_transport import calculate_wind_transport_score

        fire_clusters = []
        wind_forecast = pd.DataFrame({
            'wind_speed_10m': [10.0] * 24,
            'wind_direction_10m': [180.0] * 24
        })

        score = calculate_wind_transport_score(fire_clusters, wind_forecast)
        assert score == 0, "No fires should give transport score of 0"

    def test_calculate_wind_transport_score_single_cluster(self):
        """Test transport score with a single fire cluster."""
        from src.features.wind_transport import calculate_wind_transport_score

        # Single cluster in Sumatra
        fire_clusters = [{
            'lat': 0.5,
            'lon': 101.5,
            'total_frp': 500.0
        }]

        # Wind blowing from SW (toward Singapore)
        wind_forecast = pd.DataFrame({
            'wind_speed_10m': [15.0] * 24,
            'wind_direction_10m': [225.0] * 24  # From SW
        })

        score = calculate_wind_transport_score(fire_clusters, wind_forecast, simulation_hours=24)

        assert 0 <= score <= 100, f"Score should be 0-100, got {score}"

    def test_wind_transport_score_range(self):
        """Test that score is always in 0-100 range."""
        from src.features.wind_transport import calculate_wind_transport_score

        # Many intense clusters
        fire_clusters = [{
            'lat': 0.5 + i*0.1,
            'lon': 101.5 + i*0.1,
            'total_frp': 1000.0
        } for i in range(50)]

        wind_forecast = pd.DataFrame({
            'wind_speed_10m': [20.0] * 48,
            'wind_direction_10m': [180.0] * 48
        })

        score = calculate_wind_transport_score(fire_clusters, wind_forecast, simulation_hours=48)

        assert 0 <= score <= 100, f"Score should be capped at 100, got {score}"

    def test_trajectory_simulation(self):
        """Test that trajectory simulation produces reasonable paths."""
        from src.features.wind_transport import simulate_trajectory

        start_pos = (0.5, 101.5)

        # Steady eastward wind
        wind_forecast = pd.DataFrame({
            'wind_speed_10m': [10.0] * 24,
            'wind_direction_10m': [270.0] * 24  # From west (blowing east)
        })

        trajectory = simulate_trajectory(start_pos, wind_forecast, hours=24)

        assert len(trajectory) == 25, "Should have 25 points (0 + 24 hours)"
        assert trajectory[0] == start_pos, "First point should be start position"

        # Check that smoke moved eastward (longitude increased)
        assert trajectory[-1][1] > trajectory[0][1], "Should move east with westerly wind"

    def test_trajectory_changes_with_wind(self):
        """Test that trajectory changes direction with changing wind."""
        from src.features.wind_transport import simulate_trajectory

        start_pos = (0.5, 101.5)

        # Wind changes from eastward to northward
        wind_forecast = pd.DataFrame({
            'wind_speed_10m': [10.0] * 12 + [10.0] * 12,
            'wind_direction_10m': [270.0] * 12 + [180.0] * 12  # West then South
        })

        trajectory = simulate_trajectory(start_pos, wind_forecast, hours=24)

        # First half should move east, second half should move north
        midpoint = trajectory[12]
        endpoint = trajectory[24]

        assert midpoint[1] > start_pos[1], "Should move east in first half"
        assert endpoint[0] > midpoint[0], "Should move north in second half"

    def test_proximity_calculation(self):
        """Test proximity score calculation based on minimum distance."""
        from src.features.wind_transport import calculate_proximity_score

        # Very close trajectory (min distance 10km)
        close_score = calculate_proximity_score(min_distance=10)

        # Far trajectory (min distance 500km)
        far_score = calculate_proximity_score(min_distance=500)

        assert close_score > far_score, "Closer trajectory should have higher score"
        assert close_score == 100, "Distance < 50km should give score of 100"
        assert far_score == 0, "Distance > 200km should give score of 0"

    def test_cluster_fires(self):
        """Test fire clustering algorithm."""
        from src.features.wind_transport import cluster_fires

        # Create test fires
        fires_df = pd.DataFrame([
            {'latitude': 0.5, 'longitude': 101.5, 'frp': 100},
            {'latitude': 0.51, 'longitude': 101.51, 'frp': 150},  # Close to first
            {'latitude': 2.0, 'longitude': 105.0, 'frp': 200},    # Far from others
        ])

        clusters = cluster_fires(fires_df, radius_km=50)

        # Should create 2 clusters (first two fires are close)
        assert len(clusters) >= 1, "Should create at least one cluster"
        assert all('lat' in c and 'lon' in c and 'total_frp' in c for c in clusters), \
            "Clusters should have lat, lon, total_frp"

    def test_wind_transport_favors_singapore_direction(self):
        """Test that wind blowing toward Singapore scores higher."""
        from src.features.wind_transport import calculate_wind_transport_score

        fire_cluster = [{
            'lat': 0.5,
            'lon': 101.5,
            'total_frp': 500.0
        }]

        # Wind toward Singapore (from SW)
        favorable_wind = pd.DataFrame({
            'wind_speed_10m': [15.0] * 24,
            'wind_direction_10m': [225.0] * 24
        })

        # Wind away from Singapore (from NE)
        unfavorable_wind = pd.DataFrame({
            'wind_speed_10m': [15.0] * 24,
            'wind_direction_10m': [45.0] * 24
        })

        favorable_score = calculate_wind_transport_score(
            fire_cluster, favorable_wind, simulation_hours=24
        )
        unfavorable_score = calculate_wind_transport_score(
            fire_cluster, unfavorable_wind, simulation_hours=24
        )

        assert favorable_score > unfavorable_score, \
            "Wind toward Singapore should score higher"
