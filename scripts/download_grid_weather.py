#!/usr/bin/env python3
"""
Download historical weather data for a grid of locations.
Creates a 200km-spaced grid covering Indonesia/Malaysia fire regions.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_ingestion.weather import fetch_historical_weather
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Grid bounding box: [north, west, south, east]
# Covers Indonesia, Malaysia, up to Kalimantan
BOUNDING_BOX = [8, 95, -15, 115]

# Grid spacing in degrees (approximately 300km at equator)
# 1 degree ≈ 111km, so 300km ≈ 2.7 degrees
GRID_SPACING = 2.7

# Date range for training data
START_DATE = '2016-02-01'
END_DATE = '2024-12-31'


def generate_grid_points(bbox, spacing):
    """
    Generate grid of lat/lon points covering the bounding box.

    Args:
        bbox: [north, west, south, east]
        spacing: Grid spacing in degrees

    Returns:
        list: List of (lat, lon) tuples
    """
    north, west, south, east = bbox

    # Generate latitude and longitude arrays
    lats = np.arange(south, north + spacing, spacing)
    lons = np.arange(west, east + spacing, spacing)

    # Create grid
    grid_points = []
    for lat in lats:
        for lon in lons:
            grid_points.append((round(lat, 2), round(lon, 2)))

    return grid_points


def main():
    """Download weather data for all grid points"""

    print("=" * 60)
    print("Grid-Based Regional Weather Data Download")
    print("=" * 60)
    print(f"\nBounding box: {BOUNDING_BOX} (N, W, S, E)")
    print(f"Grid spacing: {GRID_SPACING}° (~200km)")
    print(f"Date range: {START_DATE} to {END_DATE}")

    # Generate grid
    grid_points = generate_grid_points(BOUNDING_BOX, GRID_SPACING)
    print(f"\nGenerated {len(grid_points)} grid points")
    print(f"Estimated download time: ~{len(grid_points) * 2 / 60:.1f} minutes (with rate limiting)")
    print(f"Note: Free tier may require longer delays to avoid 429 errors")
    print()

    # Create output directory
    output_dir = Path(__file__).parent.parent / "data" / "weather_grid"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}\n")

    # Check for existing progress
    output_file = output_dir / "weather_grid.csv"
    existing_grid_points = set()
    all_data = []

    if output_file.exists():
        print(f"Found existing data file: {output_file.name}")
        try:
            existing_df = pd.read_csv(output_file)
            if 'grid_lat' in existing_df.columns and 'grid_lon' in existing_df.columns:
                for _, row in existing_df[['grid_lat', 'grid_lon']].drop_duplicates().iterrows():
                    existing_grid_points.add((row['grid_lat'], row['grid_lon']))
                all_data.append(existing_df)
                print(f"Resuming: {len(existing_grid_points)} grid points already downloaded")
                print(f"Remaining: {len(grid_points) - len(existing_grid_points)} grid points\n")
        except Exception as e:
            print(f"Warning: Could not load existing data: {e}")
            print("Starting fresh download\n")

    # Download weather for each grid point
    failed_points = []

    for i, (lat, lon) in enumerate(grid_points, 1):
        # Skip if already downloaded
        if (lat, lon) in existing_grid_points:
            print(f"[{i}/{len(grid_points)}] Skipping ({lat}, {lon})... (already downloaded)")
            continue
        print(f"[{i}/{len(grid_points)}] Downloading ({lat}, {lon})...", end=" ")

        # Unlimited retry logic for rate limiting
        retry_count = 0
        success = False

        while not success:
            try:
                # Fetch historical weather
                df = fetch_historical_weather(
                    latitude=lat,
                    longitude=lon,
                    start_date=START_DATE,
                    end_date=END_DATE
                )

                if len(df) == 0:
                    print("FAILED (no data)")
                    failed_points.append((lat, lon))
                    break

                # Add grid point metadata
                df['grid_lat'] = lat
                df['grid_lon'] = lon
                df['grid_id'] = f"{lat}_{lon}"

                all_data.append(df)
                print(f"OK ({len(df):,} records)")
                success = True

                # Save progress incrementally (every successful download)
                try:
                    combined_df = pd.concat(all_data, ignore_index=True)
                    combined_df.to_csv(output_file, index=False)
                except Exception as save_error:
                    print(f" (Warning: Could not save progress: {save_error})")

            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'Too Many Requests' in error_str:
                    retry_count += 1
                    # Exponential backoff: 10s, 20s, 40s, 80s, 160s, 320s, 640s, 1200s (20min), 1800s (30min max)
                    wait_time = min(1800, 10 * (2 ** (retry_count - 1)))

                    # Format wait time for display
                    if wait_time >= 60:
                        wait_display = f"{wait_time/60:.1f}min"
                    else:
                        wait_display = f"{wait_time}s"

                    print(f"Rate limited, waiting {wait_display} (retry #{retry_count})...", end=" ", flush=True)
                    time.sleep(wait_time)
                    # Continue loop to retry
                else:
                    print(f"ERROR: {error_str}")
                    failed_points.append((lat, lon))
                    break

        # Rate limiting: delay between ALL requests
        if success:
            time.sleep(2)  # 2 second delay between successful requests

    if len(all_data) == 0:
        print("\nERROR: No data downloaded successfully!")
        return 1

    # Final save (already saved incrementally, but ensure final state is correct)
    print(f"\nFinalizing data with {len(all_data)} grid point datasets...")
    combined_df = pd.concat(all_data, ignore_index=True)

    # Count unique grid points in final dataset
    unique_points = combined_df[['grid_lat', 'grid_lon']].drop_duplicates()
    num_unique = len(unique_points)

    # Save to single CSV (overwrite with complete dataset)
    combined_df.to_csv(output_file, index=False)

    print("\n" + "=" * 60)
    print("Download Complete!")
    print("=" * 60)
    print(f"\nTotal records: {len(combined_df):,}")
    print(f"Grid points: {num_unique} successful, {len(failed_points)} failed")
    print(f"Date range: {combined_df['timestamp'].min()} to {combined_df['timestamp'].max()}")
    print(f"Memory: ~{combined_df.memory_usage(deep=True).sum() / (1024**2):.1f} MB")
    print(f"\nData saved to: {output_file}")

    if len(failed_points) > 0:
        print(f"\nFailed points ({len(failed_points)}):")
        for lat, lon in failed_points[:10]:
            print(f"  ({lat}, {lon})")
        if len(failed_points) > 10:
            print(f"  ... and {len(failed_points) - 10} more")

    print("\nNext steps:")
    print("1. Verify weather_grid.csv")
    print("2. Update training code to use grid weather")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
