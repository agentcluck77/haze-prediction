"""
Prediction logic for FastAPI endpoints
Generates PSI predictions using trained models and current data
"""

from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from typing import Optional

from src.training.model_trainer import load_model
from src.data_ingestion.firms import fetch_recent_fires
from src.data_ingestion.weather import fetch_weather_forecast
from src.data_ingestion.psi import fetch_current_psi
from src.features.fire_risk import calculate_fire_risk_score
from src.features.wind_transport import calculate_wind_transport_score, cluster_fires
from src.features.baseline import calculate_baseline_score


VALID_HORIZONS = ['24h', '48h', '72h', '7d']
HORIZON_HOURS = {
    '24h': 24,
    '48h': 48,
    '72h': 72,
    '7d': 168
}

# Model performance metrics (from validation)
MODEL_METRICS = {
    '24h': {'mae': 15.0, 'rmse': 20.0},
    '48h': {'mae': 20.0, 'rmse': 28.0},
    '72h': {'mae': 28.0, 'rmse': 38.0},
    '7d': {'mae': 40.0, 'rmse': 55.0}
}


def predict_psi(horizon: str = '24h', models_dir: str = 'models') -> dict:
    """
    Generate PSI prediction for specified horizon

    Args:
        horizon: One of '24h', '48h', '72h', '7d'
        models_dir: Directory containing trained models

    Returns:
        dict with prediction data including:
            - prediction: Predicted PSI value
            - confidence_interval: (lower, upper) bounds
            - features: Feature scores used
            - timestamp: When prediction was made
            - target_timestamp: When PSI is predicted for
            - horizon: Prediction horizon
            - model_version: Model identifier

    Raises:
        ValueError: If horizon is invalid
        FileNotFoundError: If model file not found
    """
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"Invalid horizon: {horizon}. Must be one of {VALID_HORIZONS}")

    try:
        # 1. Fetch latest data
        fires = fetch_recent_fires(days=1)
        weather = fetch_weather_forecast(
            latitude=1.3521,
            longitude=103.8198,
            hours=HORIZON_HOURS[horizon]
        )
        current_psi_data = fetch_current_psi()

        # Extract national PSI value
        if isinstance(current_psi_data, dict) and 'readings' in current_psi_data:
            # Multiple regions
            national_reading = next(
                (r for r in current_psi_data['readings']
                 if r.get('region') == 'national'),
                current_psi_data['readings'][0] if current_psi_data['readings'] else None
            )
            current_psi = national_reading['psi_24h'] if national_reading else 50
        elif 'psi' in current_psi_data:
            current_psi = current_psi_data['psi']
        else:
            # Fallback to moderate PSI
            current_psi = 50

        # 2. Compute features
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

        # 3. Load model and predict
        models_path = Path(models_dir)
        model_file = models_path / f'linear_regression_{horizon}.pkl'

        if not model_file.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_file}. "
                f"Please train models first using src/training/model_trainer.py"
            )

        model = load_model(model_file)

        # Create feature array
        features_array = np.array([[fire_risk, wind_transport, baseline]])
        prediction = model.predict(features_array)[0]

        # Ensure non-negative prediction
        prediction = max(0, prediction)

        # 4. Calculate confidence interval (±1 RMSE)
        rmse = MODEL_METRICS[horizon]['rmse']
        confidence_interval = (
            max(0, prediction - rmse),
            prediction + rmse
        )

        # 5. Calculate target timestamp
        now = datetime.now()
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
                'baseline_score': round(baseline, 1)
            },
            'timestamp': now.isoformat(),
            'target_timestamp': target_timestamp.isoformat(),
            'horizon': horizon,
            'model_version': 'phase1_linear_v1.0'
        }

    except FileNotFoundError:
        raise
    except Exception as e:
        # If data fetching fails, use fallback values
        # This allows graceful degradation
        return {
            'prediction': 50.0,
            'confidence_interval': [30.0, 70.0],
            'features': {
                'fire_risk_score': 0.0,
                'wind_transport_score': 0.0,
                'baseline_score': 50.0
            },
            'timestamp': datetime.now().isoformat(),
            'target_timestamp': (datetime.now() + timedelta(hours=HORIZON_HOURS[horizon])).isoformat(),
            'horizon': horizon,
            'model_version': 'phase1_linear_v1.0_fallback',
            'error': str(e)
        }


def predict_all_horizons(models_dir: str = 'models') -> dict:
    """
    Generate predictions for all time horizons

    Args:
        models_dir: Directory containing trained models

    Returns:
        dict mapping horizon -> prediction data
    """
    predictions = {}
    for horizon in VALID_HORIZONS:
        predictions[horizon] = predict_psi(horizon, models_dir)
    return predictions
