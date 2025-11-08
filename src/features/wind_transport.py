"""
Wind transport score calculation with trajectory simulation.
Simulates smoke trajectories and calculates transport score based on proximity to Singapore.
"""

import numpy as np
import pandas as pd
from .geospatial import haversine_distance
from sklearn.cluster import DBSCAN


def simulate_trajectory(start_pos, wind_forecast, hours=24):
    """
    Simulate smoke trajectory using hourly wind vectors.

    Args:
        start_pos: Tuple (lat, lon) starting position
        wind_forecast: DataFrame with hourly wind_speed_10m and wind_direction_10m
        hours: Number of hours to simulate

    Returns:
        list: List of (lat, lon) positions at each hour
    """
    trajectory = [start_pos]

    for hour in range(hours):
        if hour >= len(wind_forecast):
            break

        current_pos = trajectory[-1]

        # Get wind vector at current hour
        wind_speed_kmh = wind_forecast.iloc[hour]['wind_speed_10m']
        wind_direction_deg = wind_forecast.iloc[hour]['wind_direction_10m']

        # Convert to velocity components (meteorological convention)
        # Wind direction = direction FROM which wind blows
        wind_u = -wind_speed_kmh * np.sin(np.radians(wind_direction_deg))
        wind_v = -wind_speed_kmh * np.cos(np.radians(wind_direction_deg))

        # Update position (0.7 factor accounts for smoke settling/dispersion)
        # Convert km/h to degrees (rough approximation at equator: 1° ≈ 111km)
        delta_lat = (wind_v * 0.7 / 111.0)  # degrees latitude
        delta_lon = (wind_u * 0.7 / (111.0 * np.cos(np.radians(current_pos[0]))))  # degrees longitude

        new_pos = (
            current_pos[0] + delta_lat,
            current_pos[1] + delta_lon
        )
        trajectory.append(new_pos)

    return trajectory


def calculate_proximity_score(min_distance):
    """
    Calculate proximity score based on minimum distance to Singapore.

    Args:
        min_distance: Minimum distance in km

    Returns:
        float: Proximity score 0-100
    """
    if min_distance < 50:
        return 100.0
    elif min_distance < 200:
        # Linear scale from 100 to 0 between 50km and 200km
        return 100.0 * (1 - (min_distance - 50) / 150)
    else:
        return 0.0


def cluster_fires(fires_df, radius_km=50):
    """
    Cluster nearby fires using DBSCAN.

    Args:
        fires_df: DataFrame with latitude, longitude, frp columns
        radius_km: Clustering radius in kilometers

    Returns:
        list: List of fire cluster dicts with {lat, lon, total_frp}
    """
    if len(fires_df) == 0:
        return []

    # Convert lat/lon to radians for distance calculation
    coords = np.radians(fires_df[['latitude', 'longitude']].values)

    # DBSCAN clustering (epsilon in radians, ~50km / 6371km earth radius)
    eps_radians = radius_km / 6371.0
    clustering = DBSCAN(eps=eps_radians, min_samples=1, metric='haversine').fit(coords)

    clusters = []
    for cluster_id in set(clustering.labels_):
        if cluster_id == -1:
            continue  # Noise points

        cluster_mask = clustering.labels_ == cluster_id
        cluster_fires = fires_df[cluster_mask]

        # Calculate cluster centroid and total FRP
        cluster = {
            'lat': cluster_fires['latitude'].mean(),
            'lon': cluster_fires['longitude'].mean(),
            'total_frp': cluster_fires['frp'].sum()
        }
        clusters.append(cluster)

    # If no clusters formed, treat each fire as its own cluster
    if len(clusters) == 0:
        clusters = [{
            'lat': row['latitude'],
            'lon': row['longitude'],
            'total_frp': row['frp']
        } for _, row in fires_df.iterrows()]

    return clusters


def calculate_wind_transport_score(
    fire_clusters,
    wind_forecast,
    singapore_coords=(1.3521, 103.8198),
    simulation_hours=24
):
    """
    Calculate wind transport score by simulating smoke trajectories.

    Implements the algorithm from TDD.md:
    - Simulate hourly trajectories for each fire cluster
    - Find minimum distance to Singapore in each trajectory
    - Calculate proximity score (100 if <50km, linear scale to 0 at 200km)
    - Weight by cluster intensity (FRP)
    - Aggregate and cap at 100

    Args:
        fire_clusters: List of dicts with {lat, lon, total_frp}
        wind_forecast: DataFrame with hourly wind_speed_10m and wind_direction_10m
        singapore_coords: Tuple (lat, lon) for Singapore
        simulation_hours: Hours to simulate (24, 48, 72, or 168 for 7d)

    Returns:
        float: Wind transport score 0-100
    """
    if len(fire_clusters) == 0:
        return 0.0

    weighted_proximities = []

    for cluster in fire_clusters:
        # Simulate trajectory
        trajectory = simulate_trajectory(
            (cluster['lat'], cluster['lon']),
            wind_forecast,
            hours=simulation_hours
        )

        # Find minimum distance to Singapore in trajectory
        distances = [
            haversine_distance(pos, singapore_coords)
            for pos in trajectory
        ]
        min_distance = min(distances)

        # Calculate proximity score
        proximity = calculate_proximity_score(min_distance)

        # Weight by cluster intensity (normalize by 1000 MW)
        weighted_proximity = proximity * (cluster['total_frp'] / 1000.0)
        weighted_proximities.append(weighted_proximity)

    # Aggregate and cap at 100
    transport_score = min(sum(weighted_proximities), 100.0)

    return transport_score
