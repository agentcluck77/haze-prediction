"""
Fire risk score calculation.
Calculates risk score (0-100) based on FRP, distance, recency, and wind favorability.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from .geospatial import haversine_distance, bearing_to_point, angle_difference


def calculate_fire_risk_score(fires_df, singapore_coords=(1.3521, 103.8198), wind_direction=None):
    """
    Calculate fire risk score based on FRP, distance, recency, and wind favorability.

    Implements the algorithm from TDD.md:
    - Intensity weight: normalize FRP (typical range 0-500 MW)
    - Distance weight: exponential decay with 1000km characteristic distance
    - Recency weight: exponential decay with 24h half-life
    - Wind favorability: how directly wind points toward Singapore
    - Final score: scaled to 0-100 range

    Args:
        fires_df: DataFrame with columns [latitude, longitude, frp, acq_datetime]
        singapore_coords: Tuple (lat, lon) for Singapore
        wind_direction: Optional wind direction at fire locations (degrees)

    Returns:
        float: Fire risk score 0-100
    """
    if len(fires_df) == 0:
        return 0.0

    contributions = []

    for _, fire in fires_df.iterrows():
        # Intensity weight: normalize FRP (typical range 0-500 MW)
        frp = fire.get('frp', 0)
        intensity_weight = min(frp / 100.0, 1.0)

        # Distance weight: exponential decay with 1000km characteristic distance
        distance_km = haversine_distance(
            singapore_coords,
            (fire['latitude'], fire['longitude'])
        )
        distance_weight = np.exp(-distance_km / 1000.0)

        # Recency weight: exponential decay with 24h half-life
        acq_datetime = fire.get('acq_datetime')
        if acq_datetime is None or pd.isna(acq_datetime):
            # If no datetime provided, assume recent
            recency_weight = 1.0
        else:
            if isinstance(acq_datetime, str):
                acq_datetime = pd.to_datetime(acq_datetime)

            hours_old = (datetime.now() - acq_datetime).total_seconds() / 3600
            recency_weight = np.exp(-hours_old / 24.0)

        # Wind favorability: how directly wind points toward Singapore
        # If no wind direction provided, assume neutral (0.5)
        if wind_direction is None or 'wind_direction' not in fire:
            wind_favorability = 0.5
        else:
            # Calculate bearing from fire to Singapore
            bearing = bearing_to_point(
                fire['latitude'],
                fire['longitude'],
                singapore_coords[0],
                singapore_coords[1]
            )

            # Get wind direction at fire location
            fire_wind = fire.get('wind_direction', wind_direction)

            # Calculate angle difference
            wind_angle_diff = angle_difference(fire_wind, bearing)

            # Wind favorability: 1.0 when wind points directly at Singapore,
            # 0.0 when wind points directly away
            wind_favorability = 1.0 - (abs(wind_angle_diff) / 180.0)

        # Combined contribution
        contribution = (
            intensity_weight *
            distance_weight *
            recency_weight *
            wind_favorability
        )
        contributions.append(contribution)

    # Scale to 0-100 range (sum contributions and multiply by 10)
    fire_risk = min(sum(contributions) * 10, 100)

    return fire_risk
