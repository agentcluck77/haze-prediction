#!/usr/bin/env python3
"""
Download historical weather data for fire regions.
Fetches ERA5 weather for 5 key regions covering Indonesia/Malaysia fire zones.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_ingestion.weather import fetch_historical_weather
import pandas as pd
from datetime import datetime

# Define 5 key fire regions covering Indonesia/Malaysia
FIRE_REGIONS = [
    {
        'name': 'West_Sumatra',
        'lat': -0.5,
        'lon': 100.5,
        'description': 'Western Sumatra fire region'
    },
    {
        'name': 'Central_Sumatra',
        'lat': -2.0,
        'lon': 102.0,
        'description': 'Central/South Sumatra (Riau, Jambi)'
    },
    {
        'name': 'South_Sumatra',
        'lat': -3.5,
        'lon': 104.0,
        'description': 'South Sumatra (Palembang region)'
    },
    {
        'name': 'Kalimantan',
        'lat': -1.5,
        'lon': 110.0,
        'description': 'West/Central Kalimantan (Borneo)'
    },
    {
        'name': 'Peninsular_Malaysia',
        'lat': 3.5,
        'lon': 101.5,
        'description': 'Peninsular Malaysia'
    }
]

# Date range for training data
START_DATE = '2016-02-01'  # Start of training period
END_DATE = '2024-12-31'


def main():
    """Download weather data for all fire regions"""

    print("=" * 60)
    print("Regional Weather Data Download")
    print("=" * 60)
    print(f"\nDate range: {START_DATE} to {END_DATE}")
    print(f"Regions: {len(FIRE_REGIONS)}")
    print()

    # Create output directory
    output_dir = Path(__file__).parent.parent / "data" / "weather_regional"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}\n")

    # Download weather for each region
    for i, region in enumerate(FIRE_REGIONS, 1):
        print(f"[{i}/{len(FIRE_REGIONS)}] Downloading {region['name']}...")
        print(f"  Location: ({region['lat']}, {region['lon']})")
        print(f"  Description: {region['description']}")

        try:
            # Fetch historical weather
            df = fetch_historical_weather(
                latitude=region['lat'],
                longitude=region['lon'],
                start_date=START_DATE,
                end_date=END_DATE
            )

            if len(df) == 0:
                print(f"  ERROR: No data returned for {region['name']}")
                continue

            # Add region metadata
            df['region'] = region['name']
            df['region_lat'] = region['lat']
            df['region_lon'] = region['lon']

            # Save to CSV
            output_file = output_dir / f"{region['name']}.csv"
            df.to_csv(output_file, index=False)

            print(f"  Saved {len(df):,} records to {output_file.name}")
            print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"  Memory: ~{df.memory_usage(deep=True).sum() / (1024**2):.1f} MB")
            print()

        except Exception as e:
            print(f"  ERROR: Failed to download {region['name']}: {e}")
            print()
            continue

    print("=" * 60)
    print("Download Complete!")
    print("=" * 60)
    print(f"\nWeather data saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Verify CSV files in data/weather_regional/")
    print("2. Update training code to use regional weather")
    print()


if __name__ == "__main__":
    main()
