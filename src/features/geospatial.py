"""
Geospatial utility functions.
Haversine distance, bearing calculations, and angle utilities.
"""

import numpy as np


def haversine_distance(point1, point2):
    """
    Calculate great-circle distance between two points using Haversine formula.

    Args:
        point1: Tuple (latitude, longitude) in decimal degrees
        point2: Tuple (latitude, longitude) in decimal degrees

    Returns:
        float: Distance in kilometers
    """
    lat1, lon1 = point1
    lat2, lon2 = point2

    # Convert to radians
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)

    # Haversine formula
    a = (np.sin(delta_lat / 2) ** 2 +
         np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2)

    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # Earth radius in kilometers
    R = 6371.0

    distance = R * c

    return distance


def bearing_to_point(lat1, lon1, lat2, lon2):
    """
    Calculate bearing (direction) from point 1 to point 2.

    Args:
        lat1: Latitude of point 1 (decimal degrees)
        lon1: Longitude of point 1 (decimal degrees)
        lat2: Latitude of point 2 (decimal degrees)
        lon2: Longitude of point 2 (decimal degrees)

    Returns:
        float: Bearing in degrees (0-360), where:
            0° = North
            90° = East
            180° = South
            270° = West
    """
    # Convert to radians
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lon = np.radians(lon2 - lon1)

    # Calculate bearing
    x = np.sin(delta_lon) * np.cos(lat2_rad)
    y = (np.cos(lat1_rad) * np.sin(lat2_rad) -
         np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(delta_lon))

    bearing_rad = np.arctan2(x, y)

    # Convert to degrees and normalize to 0-360
    bearing = np.degrees(bearing_rad)
    bearing = (bearing + 360) % 360

    return bearing


def angle_difference(angle1, angle2):
    """
    Calculate the minimum angular difference between two angles.

    Args:
        angle1: First angle in degrees (0-360)
        angle2: Second angle in degrees (0-360)

    Returns:
        float: Minimum angle difference (0-180 degrees)
    """
    diff = abs(angle1 - angle2)

    # Handle wraparound (e.g., 10° and 350° are only 20° apart)
    if diff > 180:
        diff = 360 - diff

    return diff
