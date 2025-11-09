"""
Training data preparation.
Aligns datasets, engineers features, and creates target variables.
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from pathlib import Path
from multiprocessing import Pool, cpu_count
from src.features.fire_risk import calculate_fire_risk_score
from src.features.wind_transport import calculate_wind_transport_score, cluster_fires
from src.features.baseline import calculate_baseline_score

# Global variables for multiprocessing workers
_GLOBAL_FIRES = None
_GLOBAL_WEATHER = None
_GLOBAL_GRID_POINTS = None
_GLOBAL_PSI = None
_GLOBAL_PSI_NATIONAL = None


def align_datasets(psi_df, fire_df, weather_df):
    """
    Align PSI, fire, and weather data on timestamps.

    Args:
        psi_df: DataFrame with PSI readings
        fire_df: DataFrame with fire detections
        weather_df: DataFrame with weather data

    Returns:
        pandas.DataFrame: Aligned dataset
    """
    # Use PSI timestamps as the base
    if len(psi_df) == 0:
        return pd.DataFrame()

    # Filter for national region only
    psi_national = psi_df[psi_df['region'] == 'national'].copy()

    # Create result DataFrame
    aligned = psi_national[['timestamp', 'psi_24h']].copy()

    return aligned


def engineer_features_for_timestamp(timestamp, fires_df, weather_data, current_psi):
    """
    Engineer features for a single timestamp.

    Args:
        timestamp: Target timestamp
        fires_df: DataFrame of fires (last 72 hours)
        weather_data: DataFrame of weather forecast (next 24+ hours)
                     OR dict of regional weather DataFrames
        current_psi: Current PSI value

    Returns:
        dict: Feature dictionary with fire_risk_score, wind_transport_score, baseline_score
    """
    # Calculate fire risk score (pass timestamp for proper recency calculation in training)
    fire_risk = calculate_fire_risk_score(fires_df, reference_time=timestamp)

    # Calculate wind transport score
    if len(fires_df) > 0:
        fire_clusters = cluster_fires(fires_df)
        # weather_data can be either a single DataFrame or dict of regional DataFrames
        wind_transport = calculate_wind_transport_score(fire_clusters, weather_data, simulation_hours=24)
    else:
        wind_transport = 0.0

    # Calculate baseline score
    baseline = calculate_baseline_score(current_psi)

    return {
        'fire_risk_score': fire_risk,
        'wind_transport_score': wind_transport,
        'baseline_score': baseline
    }


def _init_worker(fires_df, weather_df, grid_points, psi_df, psi_national):
    """Initialize global data in each worker process"""
    global _GLOBAL_FIRES, _GLOBAL_WEATHER, _GLOBAL_GRID_POINTS, _GLOBAL_PSI, _GLOBAL_PSI_NATIONAL
    _GLOBAL_FIRES = fires_df
    _GLOBAL_WEATHER = weather_df
    _GLOBAL_GRID_POINTS = grid_points
    _GLOBAL_PSI = psi_df
    _GLOBAL_PSI_NATIONAL = psi_national


def _process_single_timestamp(timestamp):
    """
    Process a single timestamp (worker function for multiprocessing).

    Args:
        timestamp: Timestamp to process

    Returns:
        dict or None: Record with features and targets, or None if skipped
    """
    global _GLOBAL_FIRES, _GLOBAL_WEATHER, _GLOBAL_GRID_POINTS, _GLOBAL_PSI, _GLOBAL_PSI_NATIONAL
    from src.features.geospatial import haversine_distance

    # Get current PSI
    current_psi_row = _GLOBAL_PSI_NATIONAL[_GLOBAL_PSI_NATIONAL['timestamp'] == timestamp]
    if len(current_psi_row) == 0:
        return None

    current_psi = current_psi_row.iloc[0]['psi_24h']

    # Get fires (last 72 hours before timestamp)
    lookback_start = timestamp - timedelta(hours=72)
    fires_df = _GLOBAL_FIRES[
        (_GLOBAL_FIRES['acq_datetime'] >= lookback_start) &
        (_GLOBAL_FIRES['acq_datetime'] < timestamp)
    ].copy()

    # Get weather forecast for grid points (next 168 hours for 7d predictions)
    # Create dict mapping grid_id to weather DataFrame
    end_timestamp = timestamp + timedelta(hours=168)

    # Find unique grid points needed for fires
    fire_grid_points = set()
    if len(fires_df) > 0:
        for _, fire in fires_df.iterrows():
            # Find nearest grid point
            fire_pos = (fire['latitude'], fire['longitude'])
            min_distance = float('inf')
            nearest_point = _GLOBAL_GRID_POINTS[0]

            for grid_point in _GLOBAL_GRID_POINTS:
                distance = haversine_distance(fire_pos, grid_point)
                if distance < min_distance:
                    min_distance = distance
                    nearest_point = grid_point

            fire_grid_points.add(nearest_point)

    # Get weather for each needed grid point
    weather_forecast = {}
    for grid_lat, grid_lon in fire_grid_points:
        grid_id = f"{grid_lat}_{grid_lon}"

        # Filter to this grid point and time range
        grid_weather = _GLOBAL_WEATHER[
            (_GLOBAL_WEATHER['grid_lat'] == grid_lat) &
            (_GLOBAL_WEATHER['grid_lon'] == grid_lon) &
            (_GLOBAL_WEATHER['timestamp'] >= timestamp) &
            (_GLOBAL_WEATHER['timestamp'] < end_timestamp)
        ].copy()

        if len(grid_weather) >= 24:
            weather_forecast[grid_id] = grid_weather

    if len(weather_forecast) == 0:
        return None  # Need at least one grid point with 24h of weather data

    # Engineer features
    features = engineer_features_for_timestamp(
        timestamp, fires_df, weather_forecast, current_psi
    )

    # Create target variables
    targets = create_target_variables(_GLOBAL_PSI, timestamp)

    # Combine
    record = {
        'timestamp': timestamp,
        **features,
        **targets
    }

    return record


def create_target_variables(psi_df, base_timestamp, region='national'):
    """
    Create target PSI values at future horizons.

    Args:
        psi_df: DataFrame with PSI readings
        base_timestamp: Base timestamp to calculate from
        region: Region to get PSI for (default: national)

    Returns:
        dict: Target variables for 24h, 48h, 72h, 7d ahead
    """
    # Ensure base_timestamp is a pandas Timestamp
    base_timestamp = pd.Timestamp(base_timestamp)

    # Filter for the specified region
    psi_region = psi_df[psi_df['region'] == region].copy()
    psi_region = psi_region.sort_values('timestamp')

    # Ensure timestamp column is datetime64
    psi_region['timestamp'] = pd.to_datetime(psi_region['timestamp'])

    targets = {}

    horizons = {
        'actual_psi_24h': 24,
        'actual_psi_48h': 48,
        'actual_psi_72h': 72,
        'actual_psi_7d': 7 * 24
    }

    for target_name, hours in horizons.items():
        target_timestamp = base_timestamp + pd.Timedelta(hours=hours)

        # Find PSI reading closest to target timestamp
        psi_region['time_diff'] = (psi_region['timestamp'] - target_timestamp).abs()

        if len(psi_region) > 0:
            closest = psi_region.loc[psi_region['time_diff'].idxmin()]

            if closest['time_diff'] <= pd.Timedelta(hours=3):
                # Within 3 hours is acceptable
                targets[target_name] = closest['psi_24h']
            else:
                targets[target_name] = None
        else:
            targets[target_name] = None

    return targets


def prepare_training_dataset(start_date, end_date, sample_hours=24, use_cache=True, force_rebuild=False):
    """
    Prepare complete training dataset.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        sample_hours: Sample every N hours (default: 24 to reduce data size)
        use_cache: Use cached features if available (default: True)
        force_rebuild: Force rebuild even if cache exists (default: False)

    Returns:
        pandas.DataFrame: Training dataset with features and targets
    """
    # Check for cached features
    cache_file = Path(__file__).parent.parent.parent / "data" / "cache" / f"training_{start_date}_{end_date}_h{sample_hours}.csv"

    if use_cache and cache_file.exists() and not force_rebuild:
        print(f"Loading cached features from {cache_file.name}...")
        df = pd.read_csv(cache_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        print(f"✓ Loaded {len(df)} cached samples")
        return df

    print(f"Preparing training dataset from scratch...")
    print(f"(This will be cached for future use)")

    from src.training.historical_data import fetch_historical_psi_range
    from src.training.era5_csv_loader import load_era5_csv

    print(f"\nFetching historical data from {start_date} to {end_date}...")

    # Fetch PSI data
    psi_df = fetch_historical_psi_range(start_date, end_date)
    if len(psi_df) == 0:
        print("Warning: No PSI data found")
        return pd.DataFrame()

    # Convert timezone-aware timestamps to timezone-naive for consistency
    if psi_df['timestamp'].dt.tz is not None:
        psi_df['timestamp'] = psi_df['timestamp'].dt.tz_localize(None)

    print(f"Fetched {len(psi_df)} PSI records")

    # Load ERA5 weather data from CSV
    era5_weather, grid_points = load_era5_csv()

    if era5_weather is None or len(grid_points) == 0:
        print("ERROR: No ERA5 weather data found!")
        print("Please run: python3 scripts/convert_era5_to_csv.py")
        return pd.DataFrame()

    # Filter to requested date range
    weather_df = era5_weather[
        (era5_weather['timestamp'] >= pd.Timestamp(start_date)) &
        (era5_weather['timestamp'] <= pd.Timestamp(end_date))
    ].copy()

    print(f"Loaded {len(weather_df):,} weather records for {len(grid_points)} grid points")

    # Store grid points for worker processes
    weather_data = (weather_df, grid_points)

    # Compute national average if not present
    if 'national' not in psi_df['region'].values:
        print("Computing national average from regional data...")
        # Group by timestamp and compute mean across regions
        national_avg = psi_df.groupby('timestamp').agg({
            'psi_24h': 'mean'
        }).reset_index()
        national_avg['region'] = 'national'
        # Add to original dataframe
        psi_df = pd.concat([psi_df, national_avg], ignore_index=True)

    # Get unique timestamps from PSI (national only)
    psi_national = psi_df[psi_df['region'] == 'national'].copy()
    timestamps = psi_national['timestamp'].unique()
    timestamps = pd.to_datetime(timestamps)
    timestamps = sorted(timestamps)

    # Sample every N hours
    sampled_timestamps = timestamps[::sample_hours]

    print(f"Processing {len(sampled_timestamps)} timestamps...")

    # Batch-load ALL fire data for the entire date range at once (much faster)
    from src.training.fire_data_loader import get_fires_for_date_range

    # Calculate the full date range we need (including 3 days before start)
    fire_start_date = (pd.Timestamp(start_date) - timedelta(days=3)).strftime('%Y-%m-%d')
    fire_end_date = end_date

    print(f"Loading fire data for entire range ({fire_start_date} to {fire_end_date})...")
    all_fires = get_fires_for_date_range(fire_start_date, fire_end_date)
    print(f"Loaded {len(all_fires):,} fire records for processing")

    # Parallel processing with multiprocessing
    num_workers = cpu_count()
    print(f"Using {num_workers} CPU cores for parallel processing...")

    import time
    start_time = time.time()

    # Unpack weather data tuple
    weather_grid_df, grid_points_list = weather_data

    # Create a pool of workers
    with Pool(
        processes=num_workers,
        initializer=_init_worker,
        initargs=(all_fires, weather_grid_df, grid_points_list, psi_df, psi_national)
    ) as pool:
        # Process timestamps in parallel
        results = []
        for i, result in enumerate(pool.imap(_process_single_timestamp, sampled_timestamps)):
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                remaining = (len(sampled_timestamps) - i - 1) / rate if rate > 0 else 0
                print(f"Processing {i}/{len(sampled_timestamps)}... ({rate:.1f} timestamps/sec, ~{remaining/60:.1f} min remaining)")

            if result is not None:
                results.append(result)

    records = results
    elapsed = time.time() - start_time
    print(f"Processed {len(sampled_timestamps)} timestamps in {elapsed/60:.1f} minutes")

    if len(records) == 0:
        print("ERROR: No valid records produced!")
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Drop rows with missing targets (any horizon)
    target_columns = ['actual_psi_24h', 'actual_psi_48h', 'actual_psi_72h', 'actual_psi_7d']
    df = df.dropna(subset=target_columns)

    if len(df) == 0:
        print("\nERROR: All records dropped due to missing target values!")
        print("This likely means PSI data doesn't extend far enough into the future.")
        print(f"Date range requested: {start_date} to {end_date}")
        print("Check that PSI data extends at least 7 days beyond end_date.")
        return pd.DataFrame()

    print(f"Created training dataset with {len(df)} records")

    # Save to cache for future use
    if use_cache:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"\nSaving features to cache: {cache_file.name}...")
        df.to_csv(cache_file, index=False)
        print(f"✓ Cached {len(df)} samples ({cache_file.stat().st_size / (1024**2):.1f} MB)")

    return df
