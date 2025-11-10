#!/usr/bin/env python3
"""
Convert ERA5 GRIB file (2014-2024) to CSV format.

Usage:
    python scripts/convert_era5_grib.py <path_to_grib_file>

Example:
    python scripts/convert_era5_grib.py data/weather/era5_2014_2024.grib
"""

import sys
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.era5_weather_loader import convert_grib_to_csv


def convert_era5_data(grib_file: Path):
    """
    Convert ERA5 GRIB file to CSV format.

    Args:
        grib_file: Path to the ERA5 GRIB file (2014-2024)
    """

    # Paths
    output_csv = Path('data/weather/era5_grid.csv')
    backup_csv = Path('data/weather/era5_grid_backup.csv')

    print("=" * 70)
    print("Converting ERA5 GRIB to CSV")
    print("=" * 70)

    # Step 1: Check if GRIB file exists
    if not grib_file.exists():
        print(f"\nERROR: GRIB file not found: {grib_file}")
        print("Please provide the correct path to the downloaded GRIB file.")
        return 1

    print(f"\nGRIB file: {grib_file}")
    print(f"Size: {grib_file.stat().st_size / (1024**3):.2f} GB")

    # Step 2: Get grid points from existing CSV (if it exists)
    if output_csv.exists():
        print("\n[1/3] Reading existing CSV to get grid points...")
        existing_df = pd.read_csv(output_csv)
        print(f"  Existing data: {len(existing_df):,} records")
        print(f"  Date range: {existing_df['timestamp'].min()} to {existing_df['timestamp'].max()}")

        # Get unique grid points
        grid_points = existing_df[['grid_lat', 'grid_lon']].drop_duplicates()
        sample_points = [(lat, lon) for lat, lon in zip(grid_points['grid_lat'], grid_points['grid_lon'])]
        print(f"  Grid points: {len(sample_points)}")

        # Backup existing file
        print(f"  Backing up existing CSV to: {backup_csv}")
        existing_df.to_csv(backup_csv, index=False)
    else:
        print("\n[1/3] No existing CSV found - will extract default grid points")
        # Default grid points covering Singapore region
        # Latitude: -5 to 15, Longitude: 95 to 125 (every 0.25 degrees)
        lats = [lat for lat in range(-20, 20, 2)]  # Every 2 degrees
        lons = [lon for lon in range(90, 130, 2)]  # Every 2 degrees
        sample_points = [(lat, lon) for lat in lats for lon in lons]
        print(f"  Using {len(sample_points)} grid points")

    # Step 3: Convert GRIB to CSV
    print("\n[2/3] Converting GRIB to CSV...")
    print("  This may take 10-30 minutes depending on grid size...")

    new_df = convert_grib_to_csv(
        grib_file=grib_file,
        output_csv=output_csv,
        sample_points=sample_points
    )

    print(f"\n  Converted data: {len(new_df):,} records")
    print(f"  Date range: {new_df['timestamp'].min()} to {new_df['timestamp'].max()}")
    print(f"  File size: {output_csv.stat().st_size / (1024**2):.1f} MB")

    # Step 4: Summary
    print("\n[3/3] Verification...")

    # Check date coverage
    df_check = pd.read_csv(output_csv)
    df_check['timestamp'] = pd.to_datetime(df_check['timestamp'])

    min_date = df_check['timestamp'].min()
    max_date = df_check['timestamp'].max()

    print(f"  Start date: {min_date}")
    print(f"  End date: {max_date}")
    print(f"  Total records: {len(df_check):,}")

    # Check for 2014-2015 data
    df_2014_2015 = df_check[(df_check['timestamp'] >= '2014-01-01') & (df_check['timestamp'] < '2016-01-01')]
    print(f"  2014-2015 records: {len(df_2014_2015):,}")

    if len(df_2014_2015) == 0:
        print("  WARNING: No 2014-2015 data found!")
    else:
        print("  SUCCESS: 2014-2015 data present!")

    print("\n" + "=" * 70)
    print("SUCCESS: ERA5 GRIB converted to CSV!")
    print("=" * 70)
    if backup_csv.exists():
        print(f"\nBackup saved to: {backup_csv}")
    print(f"Output file: {output_csv}")
    print("\nNext steps:")
    print("  1. Run: python generate_eval_cache.py")
    print("  2. Run: python train_models.py")

    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python scripts/convert_era5_grib.py <path_to_grib_file>")
        print("\nExample:")
        print("  python scripts/convert_era5_grib.py data/weather/era5_2014_2024.grib")
        sys.exit(1)

    grib_file = Path(sys.argv[1])
    exit_code = convert_era5_data(grib_file)
    sys.exit(exit_code)
