#!/usr/bin/env python3
"""
Convert ERA5 GRIB to CSV for training.
Samples grid points at ~100-200km spacing for efficient training.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("=" * 60)
    print("ERA5 GRIB to CSV Converter")
    print("=" * 60)

    # Import after path setup
    from src.training.era5_weather_loader import ERA5_GRIB_FILE
    import xarray as xr

    print(f"\nLoading GRIB file: {ERA5_GRIB_FILE.name}")
    print(f"Size: {ERA5_GRIB_FILE.stat().st_size / (1024**3):.2f} GB\n")

    # Load dataset
    ds = xr.open_dataset(ERA5_GRIB_FILE, engine='cfgrib')

    print(f"Loaded dataset:")
    print(f"  Time points: {len(ds.time)}")
    print(f"  Latitude points: {len(ds.latitude)}")
    print(f"  Longitude points: {len(ds.longitude)}")
    print(f"  Total grid points: {len(ds.latitude) * len(ds.longitude):,}")
    print(f"  Memory: ~{ds.nbytes / (1024**3):.1f} GB")

    # Sample grid at ~2° spacing (~222km) for manageable size
    # Original: 0.25° spacing (93x101 = 9,393 points)
    # Sampled: ~2° spacing (~12x13 = ~150 points)
    # Time: Keep all time points (native 6-hourly resolution from ERA5)
    lat_step = 8  # Every 8th point = 2° spacing
    lon_step = 8

    sampled_lats = ds.latitude.values[::lat_step]
    sampled_lons = ds.longitude.values[::lon_step]

    print(f"\nSampling grid:")
    print(f"  Time: all time points ({len(ds.time)} points at 6-hour resolution)")
    print(f"  Latitude: every {lat_step} points ({len(sampled_lats)} points)")
    print(f"  Longitude: every {lon_step} points ({len(sampled_lons)} points)")
    print(f"  Sampled grid: {len(sampled_lats)}x{len(sampled_lons)} = {len(sampled_lats)*len(sampled_lons)} points")
    print(f"  Approximate spacing: ~{lat_step * 0.25}° (~{lat_step * 28}km)")
    print(f"  Total records: {len(ds.time) * len(sampled_lats) * len(sampled_lons):,}")

    # Extract sampled data using VECTORIZED operations (much faster!)
    print(f"\nExtracting sampled data (vectorized)...")

    # Select sampled grid points (keep all time points for continuous coverage)
    ds_sampled = ds.sel(latitude=sampled_lats, longitude=sampled_lons, method='nearest')

    print(f"  Computing wind speed and direction...")
    # Extract variables (all grid points, all times at once)
    u10 = ds_sampled['u10'].values  # Shape: (time, lat, lon)
    v10 = ds_sampled['v10'].values
    t2m = ds_sampled['t2m'].values
    sp = ds_sampled['sp'].values

    # Vectorized calculations
    wind_speed = np.sqrt(u10**2 + v10**2)
    wind_direction = (np.degrees(np.arctan2(u10, v10)) + 180) % 360
    temp_c = t2m - 273.15
    pressure_hpa = sp / 100.0

    print(f"  Reshaping data...")
    # Create coordinate grids
    times = pd.to_datetime(ds_sampled['time'].values)
    lats = ds_sampled['latitude'].values
    lons = ds_sampled['longitude'].values

    # Create meshgrid for all combinations
    time_grid, lat_grid, lon_grid = np.meshgrid(
        np.arange(len(times)),
        np.arange(len(lats)),
        np.arange(len(lons)),
        indexing='ij'
    )

    # Flatten everything
    print(f"  Creating records...")
    total_records = len(times) * len(lats) * len(lons)

    df = pd.DataFrame({
        'timestamp': times[time_grid.ravel()],
        'grid_lat': lats[lat_grid.ravel()],
        'grid_lon': lons[lon_grid.ravel()],
        'grid_id': [f"{lats[lat_grid.ravel()[i]]:.2f}_{lons[lon_grid.ravel()[i]]:.2f}"
                    for i in range(total_records)],
        'temperature_2m': temp_c.ravel(),
        'wind_speed_10m': wind_speed.ravel(),
        'wind_direction_10m': wind_direction.ravel(),
        'pressure_msl': pressure_hpa.ravel(),
    })

    print(f"  Created {len(df):,} records")

    # Save to CSV
    output_file = Path(__file__).parent.parent / "data" / "weather" / "era5_grid.csv"
    print(f"\nSaving to {output_file}...")
    df.to_csv(output_file, index=False)

    print("\n" + "=" * 60)
    print("Conversion Complete!")
    print("=" * 60)
    print(f"\nOutput file: {output_file}")
    print(f"Total records: {len(df):,}")
    print(f"Grid points: {len(sampled_lats) * len(sampled_lons)}")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"File size: {output_file.stat().st_size / (1024**2):.1f} MB")
    print(f"\nSample data:")
    print(df.head(10))

    print("\n" + "=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
