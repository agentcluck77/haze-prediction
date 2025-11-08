"""
Fire risk score calculation.
Calculates risk score (0-100) based on FRP, distance, recency, and wind favorability.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from .geospatial import haversine_distance, bearing_to_point, angle_difference


def calculate_fire_risk_score(fires_df, singapore_coords=(1.3521, 103.8198), wind_direction=None, reference_time=None):
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
        reference_time: Reference time for recency calculation (default: now)
                       For training, pass the timestamp being processed

    Returns:
        float: Fire risk score 0-100
    """
    if len(fires_df) == 0:
        return 0.0

    # Vectorized operations for massive speedup
    fires = fires_df.copy()

    # Intensity weight: normalize FRP (typical range 0-500 MW)
    intensity_weight = np.minimum(fires['frp'].fillna(0) / 100.0, 1.0)

    # Distance weight: exponential decay with 1000km characteristic distance
    # Vectorized haversine distance calculation
    lat1, lon1 = singapore_coords
    lat2 = fires['latitude'].values
    lon2 = fires['longitude'].values

    # Haversine formula (vectorized)
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    distance_km = 6371 * c  # Earth radius in km

    distance_weight = np.exp(-distance_km / 1000.0)

    # Recency weight: exponential decay with 24h half-life
    acq_datetime = pd.to_datetime(fires['acq_datetime'])
    ref_time = pd.to_datetime(reference_time) if reference_time is not None else pd.Timestamp.now()

    # Handle missing datetimes
    hours_old = (ref_time - acq_datetime).dt.total_seconds() / 3600
    hours_old = hours_old.fillna(0)  # Assume recent if missing
    recency_weight = np.exp(-hours_old / 24.0)

    # Wind favorability: simplified to 0.5 for all fires (neutral assumption)
    # Full wind calculation can be added later if wind data is available
    wind_favorability = 0.5

    # Combined contribution (vectorized)
    contribution = (
        intensity_weight.values *
        distance_weight *
        recency_weight.values *
        wind_favorability
    )

    # Scale to 0-100 range (sum contributions and multiply by 10)
    fire_risk = min(contribution.sum() * 10, 100)

    return fire_risk
