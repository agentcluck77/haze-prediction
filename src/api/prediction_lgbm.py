"""
LightGBM-based prediction logic for FastAPI endpoints
Generates PSI predictions using LightGBM models with 25 features
"""

from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Optional
import os
import joblib

from src.data_ingestion.firms import fetch_recent_fires
from src.data_ingestion.weather import fetch_weather_forecast
from src.data_ingestion.psi import fetch_current_psi
from src.features.fire_risk import calculate_fire_risk_score
from src.features.wind_transport import calculate_wind_transport_score, cluster_fires
from src.features.baseline import calculate_baseline_score
from src.features.geospatial import haversine_distance


# Get satellite from environment or use default
FIRMS_SATELLITE = os.getenv('FIRMS_SATELLITE', 'MODIS_NRT')

# Singapore coordinates
SINGAPORE_LAT = 1.3521
SINGAPORE_LON = 103.8198

VALID_HORIZONS = ['24h', '48h', '72h', '7d']
HORIZON_HOURS = {
    '24h': 24,
    '48h': 48,
    '72h': 72,
    '7d': 168
}

# Distance bands for fire spatial features (in km)
DISTANCE_BANDS = {
    'near': (0, 250),
    'medium': (250, 500),
    'far': (500, 1000),
    'very_far': (1000, float('inf'))
}


def calculate_psi_lag_features(current_psi: float) -> dict:
    """
    Calculate PSI lag features

    For real-time API, we use simplified approach:
    - Use current PSI as fallback for all lag features
    - In production, these would come from a database of historical readings

    Args:
        current_psi: Current PSI value

    Returns:
        dict with lag feature values
    """
    # Fallback: assume stable PSI over recent hours
    # In production, fetch from database or cache
    return {
        'psi_lag_1h': current_psi,
        'psi_lag_6h': current_psi,
        'psi_lag_12h': current_psi,
        'psi_lag_24h': current_psi,
        'psi_trend_1h_6h': 0.0,  # No change
        'psi_trend_6h_24h': 0.0  # No change
    }


def calculate_temporal_features(timestamp: datetime) -> dict:
    """
    Calculate temporal features from timestamp

    Args:
        timestamp: Current datetime

    Returns:
        dict with temporal feature values
    """
    # Determine season (0=SW Monsoon/haze season, 1=NE Monsoon/wet, 2=Inter-monsoon)
    month = timestamp.month
    if month in [6, 7, 8, 9]:
        season = 0  # SW Monsoon (June-Sep) - haze season
    elif month in [12, 1, 2, 3]:
        season = 1  # NE Monsoon (Dec-Mar) - wet season
    else:
        season = 2  # Inter-monsoon

    return {
        'hour': timestamp.hour,
        'day_of_week': timestamp.weekday(),
        'month': timestamp.month,
        'day_of_year': timestamp.timetuple().tm_yday,
        'season': season
    }


def calculate_fire_spatial_features(fires: pd.DataFrame) -> dict:
    """
    Calculate fire spatial features by distance bands

    Args:
        fires: DataFrame with fire detections (lat, lon, frp columns)

    Returns:
        dict with fire spatial feature values (12 features)
    """
    if len(fires) == 0:
        # No fires - return zeros
        features = {}
        for band_name in DISTANCE_BANDS.keys():
            features[f'fire_count_{band_name}'] = 0
            features[f'fire_frp_sum_{band_name}'] = 0.0
            features[f'fire_frp_mean_{band_name}'] = 0.0
        return features

    # Calculate distance for each fire
    fires = fires.copy()
    fires['distance_km'] = fires.apply(
        lambda row: haversine_distance(
            (SINGAPORE_LAT, SINGAPORE_LON),
            (row['latitude'], row['longitude'])
        ),
        axis=1
    )

    # Calculate features for each distance band
    features = {}
    for band_name, (min_dist, max_dist) in DISTANCE_BANDS.items():
        band_fires = fires[(fires['distance_km'] >= min_dist) & (fires['distance_km'] < max_dist)]

        count = len(band_fires)
        frp_sum = band_fires['frp'].sum() if count > 0 else 0.0
        frp_mean = band_fires['frp'].mean() if count > 0 else 0.0

        features[f'fire_count_{band_name}'] = count
        features[f'fire_frp_sum_{band_name}'] = frp_sum
        features[f'fire_frp_mean_{band_name}'] = frp_mean

    return features


def predict_psi_lgbm(horizon: str = '24h', models_dir: str = 'models') -> dict:
    """
    Generate PSI prediction using LightGBM model with 25 features

    Args:
        horizon: One of '24h', '48h', '72h', '7d'
        models_dir: Directory containing trained models

    Returns:
        dict with prediction data

    Raises:
        ValueError: If horizon is invalid
        FileNotFoundError: If model file not found
    """
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"Invalid horizon: {horizon}. Must be one of {VALID_HORIZONS}")

    try:
        # 1. Fetch latest data
        fires = fetch_recent_fires(days=1, satellite=FIRMS_SATELLITE)
        weather = fetch_weather_forecast(
            latitude=SINGAPORE_LAT,
            longitude=SINGAPORE_LON,
            hours=HORIZON_HOURS[horizon]
        )
        current_psi_data = fetch_current_psi()

        # Extract national PSI value
        if isinstance(current_psi_data, dict) and 'readings' in current_psi_data:
            national_reading = next(
                (r for r in current_psi_data['readings']
                 if r.get('region') == 'national'),
                current_psi_data['readings'][0] if current_psi_data['readings'] else None
            )
            current_psi = national_reading['psi_24h'] if national_reading else 50
        elif 'psi' in current_psi_data:
            current_psi = current_psi_data['psi']
        else:
            current_psi = 50

        # 2. Compute all 25 features
        now = datetime.now()

        # Original 3 features
        fire_risk = calculate_fire_risk_score(fires) if len(fires) > 0 else 0.0

        if len(fires) > 0:
            fire_clusters = cluster_fires(fires)
            wind_transport = calculate_wind_transport_score(
                fire_clusters,
                weather,
                simulation_hours=HORIZON_HOURS[horizon]
            )
        else:
            wind_transport = 0.0

        baseline = calculate_baseline_score(current_psi)

        # PSI lag features (6)
        psi_lag_features = calculate_psi_lag_features(current_psi)

        # Temporal features (5)
        temporal_features = calculate_temporal_features(now)

        # Fire spatial features (12)
        fire_spatial_features = calculate_fire_spatial_features(fires)

        # 3. Create feature array in correct order (must match training)
        features = {
            'fire_risk_score': fire_risk,
            'wind_transport_score': wind_transport,
            'baseline_score': baseline,
            **psi_lag_features,
            **temporal_features,
            **fire_spatial_features
        }

        # Ensure correct order (same as training)
        feature_order = [
            'fire_risk_score', 'wind_transport_score', 'baseline_score',
            'psi_lag_1h', 'psi_lag_6h', 'psi_lag_12h', 'psi_lag_24h',
            'psi_trend_1h_6h', 'psi_trend_6h_24h',
            'hour', 'day_of_week', 'month', 'day_of_year', 'season',
            'fire_count_near', 'fire_frp_sum_near', 'fire_frp_mean_near',
            'fire_count_medium', 'fire_frp_sum_medium', 'fire_frp_mean_medium',
            'fire_count_far', 'fire_frp_sum_far', 'fire_frp_mean_far',
            'fire_count_very_far', 'fire_frp_sum_very_far', 'fire_frp_mean_very_far'
        ]

        features_array = np.array([[features[col] for col in feature_order]])

        # 4. Load LightGBM model and predict
        models_path = Path(models_dir)
        model_file = models_path / f'lightgbm_{horizon}.pkl'

        if not model_file.exists():
            raise FileNotFoundError(
                f"LightGBM model file not found: {model_file}. "
                f"Please train models first using train_models_lgbm.py"
            )

        model = joblib.load(model_file)
        prediction = model.predict(features_array)[0]

        # Ensure non-negative prediction
        prediction = max(0, prediction)

        # 5. Calculate confidence interval (±1.5 RMSE for LightGBM)
        # LightGBM is more confident, so slightly tighter interval
        rmse = {
            '24h': 7.5, '48h': 8.8, '72h': 8.8, '7d': 9.6
        }[horizon]

        confidence_interval = (
            max(0, prediction - rmse),
            prediction + rmse
        )

        # 6. Calculate target timestamp
        hours_ahead = HORIZON_HOURS[horizon]
        target_timestamp = now + timedelta(hours=hours_ahead)

        return {
            'prediction': round(prediction, 1),
            'confidence_interval': [
                round(confidence_interval[0], 1),
                round(confidence_interval[1], 1)
            ],
            'features': {
                'fire_risk_score': round(fire_risk, 1),
                'wind_transport_score': round(wind_transport, 1),
                'baseline_score': round(baseline, 1),
                'fire_count_total': len(fires),
                'current_psi': round(current_psi, 1)
            },
            'timestamp': now.isoformat(),
            'target_timestamp': target_timestamp.isoformat(),
            'horizon': horizon,
            'model_version': 'lightgbm_v1.0_25features'
        }

    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f"LightGBM prediction failed for {horizon}: {str(e)}") from e


def predict_all_horizons_lgbm(models_dir: str = 'models') -> dict:
    """
    Generate predictions for all horizons using LightGBM

    Optimized to fetch data once and reuse for all horizons

    Args:
        models_dir: Directory containing trained models

    Returns:
        dict mapping horizon -> prediction data
    """
    try:
        # 1. Fetch latest data ONCE
        fires = fetch_recent_fires(days=1, satellite=FIRMS_SATELLITE)
        current_psi_data = fetch_current_psi()

        # Extract national PSI value
        if isinstance(current_psi_data, dict) and 'readings' in current_psi_data:
            national_reading = next(
                (r for r in current_psi_data['readings']
                 if r.get('region') == 'national'),
                current_psi_data['readings'][0] if current_psi_data['readings'] else None
            )
            current_psi = national_reading['psi_24h'] if national_reading else 50
        elif 'psi' in current_psi_data:
            current_psi = current_psi_data['psi']
        else:
            current_psi = 50

        # Fetch weather once for longest horizon
        max_hours = max(HORIZON_HOURS.values())
        weather_full = fetch_weather_forecast(
            latitude=SINGAPORE_LAT,
            longitude=SINGAPORE_LON,
            hours=max_hours
        )

        # Calculate shared features once
        now = datetime.now()
        fire_risk = calculate_fire_risk_score(fires) if len(fires) > 0 else 0.0
        baseline = calculate_baseline_score(current_psi)
        fire_clusters = cluster_fires(fires) if len(fires) > 0 else None
        psi_lag_features = calculate_psi_lag_features(current_psi)
        temporal_features = calculate_temporal_features(now)
        fire_spatial_features = calculate_fire_spatial_features(fires)

        # 2. Generate predictions for each horizon
        predictions = {}

        for horizon in VALID_HORIZONS:
            try:
                # Slice weather data for this horizon
                hours_needed = HORIZON_HOURS[horizon]
                weather = weather_full.head(hours_needed) if len(weather_full) > 0 else weather_full

                # Calculate wind transport for this horizon
                if fire_clusters is not None:
                    wind_transport = calculate_wind_transport_score(
                        fire_clusters,
                        weather,
                        simulation_hours=hours_needed
                    )
                else:
                    wind_transport = 0.0

                # Create feature array
                features = {
                    'fire_risk_score': fire_risk,
                    'wind_transport_score': wind_transport,
                    'baseline_score': baseline,
                    **psi_lag_features,
                    **temporal_features,
                    **fire_spatial_features
                }

                feature_order = [
                    'fire_risk_score', 'wind_transport_score', 'baseline_score',
                    'psi_lag_1h', 'psi_lag_6h', 'psi_lag_12h', 'psi_lag_24h',
                    'psi_trend_1h_6h', 'psi_trend_6h_24h',
                    'hour', 'day_of_week', 'month', 'day_of_year', 'season',
                    'fire_count_near', 'fire_frp_sum_near', 'fire_frp_mean_near',
                    'fire_count_medium', 'fire_frp_sum_medium', 'fire_frp_mean_medium',
                    'fire_count_far', 'fire_frp_sum_far', 'fire_frp_mean_far',
                    'fire_count_very_far', 'fire_frp_sum_very_far', 'fire_frp_mean_very_far'
                ]

                features_array = np.array([[features[col] for col in feature_order]])

                # Load model and predict
                models_path = Path(models_dir)
                model_file = models_path / f'lightgbm_{horizon}.pkl'

                if not model_file.exists():
                    raise FileNotFoundError(f"LightGBM model not found: {model_file}")

                model = joblib.load(model_file)
                prediction = model.predict(features_array)[0]
                prediction = max(0, prediction)

                # Calculate confidence interval
                rmse = {
                    '24h': 7.5, '48h': 8.8, '72h': 8.8, '7d': 9.6
                }[horizon]

                confidence_interval = (
                    max(0, prediction - rmse),
                    prediction + rmse
                )

                # Calculate target timestamp
                hours_ahead = HORIZON_HOURS[horizon]
                target_timestamp = now + timedelta(hours=hours_ahead)

                predictions[horizon] = {
                    'prediction': round(prediction, 1),
                    'confidence_interval': [
                        round(confidence_interval[0], 1),
                        round(confidence_interval[1], 1)
                    ],
                    'features': {
                        'fire_risk_score': round(fire_risk, 1),
                        'wind_transport_score': round(wind_transport, 1),
                        'baseline_score': round(baseline, 1),
                        'fire_count_total': len(fires),
                        'current_psi': round(current_psi, 1)
                    },
                    'timestamp': now.isoformat(),
                    'target_timestamp': target_timestamp.isoformat(),
                    'horizon': horizon,
                    'model_version': 'lightgbm_v1.0_25features'
                }

            except Exception as e:
                raise RuntimeError(f"Prediction failed for {horizon}: {str(e)}") from e

        return predictions

    except Exception as e:
        raise RuntimeError(f"Failed to generate predictions: {str(e)}") from e
