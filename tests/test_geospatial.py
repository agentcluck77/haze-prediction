"""
Test geospatial utility functions.
Following TDD protocol: Write tests first, then implement.
"""

import pytest
import numpy as np


class TestGeospatialUtils:
    """Test suite for geospatial calculations."""

    def test_haversine_distance_same_point(self):
        """Test that distance from a point to itself is zero."""
        from src.features.geospatial import haversine_distance

        distance = haversine_distance((1.3521, 103.8198), (1.3521, 103.8198))
        assert distance == pytest.approx(0, abs=0.1), "Distance to same point should be zero"

    def test_haversine_distance_singapore_to_jakarta(self):
        """Test distance between Singapore and Jakarta."""
        from src.features.geospatial import haversine_distance

        singapore = (1.3521, 103.8198)
        jakarta = (-6.2088, 106.8456)

        distance = haversine_distance(singapore, jakarta)

        # Approx 900 km
        assert 850 < distance < 950, f"Distance should be ~900km, got {distance}km"

    def test_bearing_to_point(self):
        """Test bearing calculation from one point to another."""
        from src.features.geospatial import bearing_to_point

        # From Singapore (1.35, 103.82) to a point north should be ~0 degrees
        bearing = bearing_to_point(1.3521, 103.8198, 2.0, 103.8198)

        assert 350 < bearing or bearing < 10, f"Bearing north should be ~0°, got {bearing}°"

    def test_bearing_to_point_southeast(self):
        """Test bearing calculation to southeast."""
        from src.features.geospatial import bearing_to_point

        # From origin to southeast quadrant should be 90-180 degrees
        bearing = bearing_to_point(0, 0, -1, 1)

        assert 90 < bearing < 180, f"Bearing to SE should be 90-180°, got {bearing}°"

    def test_angle_difference(self):
        """Test calculation of angular difference."""
        from src.features.geospatial import angle_difference

        # Same angle
        assert angle_difference(90, 90) == 0

        # Opposite angles
        assert angle_difference(0, 180) == 180
        assert angle_difference(180, 0) == 180

        # Wraparound
        diff = angle_difference(10, 350)
        assert diff == pytest.approx(20, abs=1), f"Angle diff should be 20°, got {diff}°"

    def test_angle_difference_range(self):
        """Test that angle difference is always 0-180."""
        from src.features.geospatial import angle_difference

        for a1 in [0, 45, 90, 135, 180, 225, 270, 315]:
            for a2 in [0, 45, 90, 135, 180, 225, 270, 315]:
                diff = angle_difference(a1, a2)
                assert 0 <= diff <= 180, f"Angle diff should be 0-180°, got {diff}°"
