#!/usr/bin/env python3
"""
Inspect ERA5 GRIB file to see what variables and dimensions it contains.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.era5_weather_loader import ERA5_GRIB_FILE

def main():
    print("=" * 60)
    print("ERA5 GRIB File Inspection")
    print("=" * 60)
    print(f"\nFile: {ERA5_GRIB_FILE}")
    print(f"Size: {ERA5_GRIB_FILE.stat().st_size / (1024**3):.2f} GB\n")

    try:
        import xarray as xr
        print("Loading GRIB file (this may take a minute)...")

        # Try loading without filtering first
        ds = xr.open_dataset(ERA5_GRIB_FILE, engine='cfgrib')

        print("\n" + "=" * 60)
        print("Dataset Overview")
        print("=" * 60)
        print(ds)

        print("\n" + "=" * 60)
        print("Variables")
        print("=" * 60)
        for var in ds.data_vars:
            print(f"  {var}: {ds[var].dims} - {ds[var].attrs.get('long_name', 'N/A')}")

        print("\n" + "=" * 60)
        print("Dimensions")
        print("=" * 60)
        for dim in ds.dims:
            print(f"  {dim}: {ds.dims[dim]}")

        print("\n" + "=" * 60)
        print("Coordinates")
        print("=" * 60)
        for coord in ds.coords:
            values = ds.coords[coord].values
            if len(values) > 10:
                print(f"  {coord}: {values[0]} to {values[-1]} ({len(values)} points)")
            else:
                print(f"  {coord}: {values}")

        print("\n" + "=" * 60)
        print("Sample Data Point")
        print("=" * 60)
        # Get first timestep, middle of lat/lon grid
        sample = ds.isel(time=0)
        if 'latitude' in ds.dims:
            sample = sample.isel(latitude=len(ds.latitude)//2)
        if 'longitude' in ds.dims:
            sample = sample.isel(longitude=len(ds.longitude)//2)

        print(sample)

    except ImportError as e:
        print(f"\nERROR: Missing required library: {e}")
        print("\nInstall with:")
        print("  pip install xarray cfgrib eccodes")
        return 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
