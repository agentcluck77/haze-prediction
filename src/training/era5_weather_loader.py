"""
ERA5 GRIB weather data loader.
Loads ERA5 data from GRIB format and provides spatial/temporal lookups.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Global cache for ERA5 data
_ERA5_CACHE = None

# Path to ERA5 GRIB file
ERA5_GRIB_FILE = Path(__file__).parent.parent.parent / "data" / "weather" / "f7fc7094c3a622b1b783338b67446c0f.grib"


def load_era5_data(grib_file=None):
    """
    Load ERA5 data from GRIB file.

    Requires: xarray, cfgrib
    Install with: pip install xarray cfgrib eccodes

    Args:
        grib_file: Path to GRIB file (optional, uses default if not provided)

    Returns:
        xarray.Dataset: ERA5 weather data
    """
    global _ERA5_CACHE

    if _ERA5_CACHE is not None:
        return _ERA5_CACHE

    if grib_file is None:
        grib_file = ERA5_GRIB_FILE

    print(f"Loading ERA5 data from {grib_file}...")

    try:
        import xarray as xr
    except ImportError:
        raise ImportError(
            "xarray is required to read GRIB files. "
            "Install with: pip install xarray cfgrib eccodes"
        )

    # Load GRIB file
    # ERA5 GRIB files may have multiple variables with different time dimensions
    # Use errors='ignore' to skip problematic variables
    print(f"Loading ERA5 data from {grib_file}...")
    ds = xr.open_dataset(
        grib_file,
        engine='cfgrib',
        backend_kwargs={
            'errors': 'ignore',  # Skip variables that cause conflicts
            'indexpath': ''  # Don't use index files (can cause issues)
        }
    )

    print(f"Loaded ERA5 dataset")
    print(f"  Variables: {list(ds.data_vars)}")
    print(f"  Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
    print(f"  Lat range: {ds.latitude.values.min()} to {ds.latitude.values.max()}")
    print(f"  Lon range: {ds.longitude.values.min()} to {ds.longitude.values.max()}")
    print(f"  Memory: ~{ds.nbytes / (1024**3):.1f} GB")

    _ERA5_CACHE = ds
    return ds


def calculate_wind_speed_direction(u10, v10):
    """
    Calculate wind speed and direction from u/v components.

    Args:
        u10: 10m u-component (east-west)
        v10: 10m v-component (north-south)

    Returns:
        tuple: (wind_speed, wind_direction)
            wind_speed in m/s (or original units)
            wind_direction in degrees (0-360, meteorological convention)
    """
    # Wind speed (magnitude)
    wind_speed = np.sqrt(u10**2 + v10**2)

    # Wind direction (meteorological: direction FROM which wind blows)
    # atan2(u, v) gives direction TO which wind blows
    # Add 180 and modulo to get direction FROM
    wind_direction = (np.degrees(np.arctan2(u10, v10)) + 180) % 360

    return wind_speed, wind_direction


def get_weather_at_location(lat, lon, timestamp, forecast_hours=168, grib_file=None):
    """
    Get weather data at a specific location and time.

    Args:
        lat: Latitude
        lon: Longitude
        timestamp: Starting timestamp
        forecast_hours: Hours of data needed
        grib_file: Path to GRIB file (optional)

    Returns:
        pandas.DataFrame: Weather data with columns:
            timestamp, temperature_2m, wind_speed_10m, wind_direction_10m, pressure_msl
    """
    ds = load_era5_data(grib_file)

    # Convert timestamp to numpy datetime64
    start_time = pd.to_datetime(timestamp)
    end_time = start_time + timedelta(hours=forecast_hours)

    # Find nearest grid point
    lat_idx = np.argmin(np.abs(ds.latitude.values - lat))
    lon_idx = np.argmin(np.abs(ds.longitude.values - lon))

    # Extract time slice
    ds_location = ds.sel(
        latitude=ds.latitude.values[lat_idx],
        longitude=ds.longitude.values[lon_idx],
        method='nearest'
    )

    # Filter time range
    ds_time = ds_location.sel(time=slice(start_time, end_time))

    # Extract variables and calculate wind
    times = pd.to_datetime(ds_time.time.values)

    # Get u/v wind components
    u10 = ds_time['u10'].values if 'u10' in ds_time else ds_time['10u'].values
    v10 = ds_time['v10'].values if 'v10' in ds_time else ds_time['10v'].values

    wind_speed, wind_direction = calculate_wind_speed_direction(u10, v10)

    # Get other variables
    temp_2m = ds_time['t2m'].values if 't2m' in ds_time else ds_time['2t'].values
    pressure = ds_time['sp'].values if 'sp' in ds_time else None

    # Convert temperature from K to C if needed
    if temp_2m.mean() > 100:  # Likely in Kelvin
        temp_2m = temp_2m - 273.15

    # Convert pressure from Pa to hPa if needed
    if pressure is not None and pressure.mean() > 10000:  # Likely in Pa
        pressure = pressure / 100.0

    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': times,
        'temperature_2m': temp_2m,
        'wind_speed_10m': wind_speed,
        'wind_direction_10m': wind_direction,
        'pressure_msl': pressure if pressure is not None else np.nan,
        'latitude': lat,
        'longitude': lon
    })

    return df


def convert_grib_to_csv(grib_file, output_csv, sample_points=None):
    """
    Convert GRIB file to CSV - FAST version loads all data once.

    Args:
        grib_file: Path to GRIB file
        output_csv: Path to output CSV
        sample_points: List of (lat, lon) tuples to extract (optional, extracts all if None)
    """
    ds = load_era5_data(grib_file)

    print(f"Converting GRIB to CSV...")

    if sample_points:
        total_points = len(sample_points)
        print(f"Extracting {total_points} grid points...")

        # KEY OPTIMIZATION: Load ALL data into memory ONCE (~35 seconds)
        # This is 150x faster than loading point-by-point (86 minutes)
        print(f"Loading all data into memory (~35 seconds, uses ~2.3GB RAM)...")
        ds_loaded = ds.load()
        print(f"Data loaded! Now extracting points (fast)...")

        all_dfs = []

        for idx, (lat, lon) in enumerate(sample_points, 1):
            if idx % 20 == 0 or idx == 1:
                print(f"  Progress: {idx}/{total_points}")

            # Find nearest grid point
            lat_idx = np.argmin(np.abs(ds_loaded.latitude.values - lat))
            lon_idx = np.argmin(np.abs(ds_loaded.longitude.values - lon))

            # Extract from in-memory dataset (INSTANT!)
            times = pd.to_datetime(ds_loaded.time.values)
            u10 = ds_loaded['u10'].values[:, lat_idx, lon_idx]
            v10 = ds_loaded['v10'].values[:, lat_idx, lon_idx]
            temp_2m = ds_loaded['t2m'].values[:, lat_idx, lon_idx]
            pressure = ds_loaded['sp'].values[:, lat_idx, lon_idx] if 'sp' in ds_loaded else np.zeros(len(times))

            # Calculate wind speed/direction vectorized
            wind_speed = np.sqrt(u10**2 + v10**2)
            wind_direction = (np.degrees(np.arctan2(u10, v10)) + 180) % 360

            # Convert units (vectorized)
            temp_2m = np.where(temp_2m > 100, temp_2m - 273.15, temp_2m)
            pressure = np.where(pressure > 10000, pressure / 100.0, pressure)

            # Create DataFrame for this grid point
            point_df = pd.DataFrame({
                'timestamp': times,
                'grid_lat': float(ds_loaded.latitude.values[lat_idx]),
                'grid_lon': float(ds_loaded.longitude.values[lon_idx]),
                'temperature_2m': temp_2m,
                'wind_speed_10m': wind_speed,
                'wind_direction_10m': wind_direction,
                'pressure_msl': pressure
            })

            all_dfs.append(point_df)

    else:
        raise NotImplementedError("Full grid extraction not implemented - use sample_points")

    # Combine all DataFrames
    print(f"Combining {len(all_dfs)} grid points...")
    df = pd.concat(all_dfs, ignore_index=True)

    # Save to CSV
    print(f"Saving to CSV...")
    df.to_csv(output_csv, index=False)

    print(f"Saved {len(df):,} records to {output_csv}")
    print(f"File size: ~{Path(output_csv).stat().st_size / (1024**2):.1f} MB")

    return df


def clear_cache():
    """Clear the ERA5 cache to free memory"""
    global _ERA5_CACHE
    if _ERA5_CACHE is not None:
        _ERA5_CACHE.close()
    _ERA5_CACHE = None
    print("ERA5 cache cleared")
