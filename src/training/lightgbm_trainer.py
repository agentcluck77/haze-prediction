"""
LightGBM model training module for PSI prediction
Implements training with class weighting to handle imbalance
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from lightgbm import LGBMRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error


VALID_HORIZONS = ['24h', '48h', '72h', '7d']

# All 25 features (3 original + 22 new features)
FEATURE_COLUMNS = [
    # Original features (3)
    'fire_risk_score',
    'wind_transport_score',
    'baseline_score',

    # PSI lag features (6)
    'psi_lag_1h',
    'psi_lag_6h',
    'psi_lag_12h',
    'psi_lag_24h',
    'psi_trend_1h_6h',
    'psi_trend_6h_24h',

    # Temporal features (5)
    'hour',
    'day_of_week',
    'month',
    'day_of_year',
    'season',

    # Fire spatial features (12)
    'fire_count_near',
    'fire_frp_sum_near',
    'fire_frp_mean_near',
    'fire_count_medium',
    'fire_frp_sum_medium',
    'fire_frp_mean_medium',
    'fire_count_far',
    'fire_frp_sum_far',
    'fire_frp_mean_far',
    'fire_count_very_far',
    'fire_frp_sum_very_far',
    'fire_frp_mean_very_far'
]

MINIMUM_SAMPLES = 5


def calculate_sample_weights(y: pd.Series, psi_thresholds=[0, 50, 100, 200, 300]) -> np.ndarray:
    """
    Calculate sample weights to handle class imbalance

    Assigns higher weights to samples in minority classes (unhealthy PSI)

    Args:
        y: Target PSI values
        psi_thresholds: Thresholds defining PSI bands

    Returns:
        Array of sample weights (higher for rare classes)
    """
    # Categorize PSI values into bands
    categories = pd.cut(y, bins=[-np.inf] + psi_thresholds + [np.inf], labels=False)

    # Calculate class frequencies
    class_counts = categories.value_counts().sort_index()
    n_samples = len(y)

    # Calculate weights: inverse of class frequency
    # Weight = n_samples / (n_classes * n_samples_in_class)
    n_classes = len(class_counts)
    class_weights = {}
    for class_id, count in class_counts.items():
        if count > 0:
            class_weights[class_id] = n_samples / (n_classes * count)
        else:
            class_weights[class_id] = 0.0

    # Map weights to samples
    sample_weights = categories.map(class_weights).fillna(1.0).values

    return sample_weights


def train_lightgbm_model(training_data: pd.DataFrame, horizon: str,
                          test_size: float = 0.2, random_state: int = 42) -> dict:
    """
    Train a LightGBM model with class weighting for imbalance

    Args:
        training_data: DataFrame with features and target
        horizon: One of '24h', '48h', '72h', '7d'
        test_size: Fraction for test set (default 0.2)
        random_state: Random seed

    Returns:
        dict with 'model', 'metrics_train', 'metrics_test', 'feature_importance'

    Raises:
        ValueError: If horizon invalid or insufficient data
    """
    # Validate horizon
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"Invalid horizon: {horizon}. Must be one of {VALID_HORIZONS}")

    # Check minimum samples
    if len(training_data) < MINIMUM_SAMPLES:
        raise ValueError(
            f"Insufficient training data: {len(training_data)} samples. "
            f"Minimum required: {MINIMUM_SAMPLES}"
        )

    # Extract features and target
    target_col = f'actual_psi_{horizon}'
    X = training_data[FEATURE_COLUMNS]
    y = training_data[target_col]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Calculate sample weights for training set
    sample_weights = calculate_sample_weights(y_train)

    # LightGBM parameters optimized for imbalanced regression
    model = LGBMRegressor(
        n_estimators=200,           # Number of trees
        learning_rate=0.05,          # Conservative learning rate
        max_depth=6,                 # Prevent overfitting
        num_leaves=31,               # Default for max_depth=6
        min_child_samples=20,        # Require at least 20 samples per leaf
        subsample=0.8,               # Use 80% of data per tree
        colsample_bytree=0.8,        # Use 80% of features per tree
        reg_alpha=0.1,               # L1 regularization
        reg_lambda=0.1,              # L2 regularization
        random_state=random_state,
        n_jobs=-1,                   # Use all CPU cores
        verbose=-1                   # Suppress output
    )

    # Train with sample weights
    model.fit(X_train, y_train, sample_weight=sample_weights)

    # Calculate metrics
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    metrics_train = {
        'mae': mean_absolute_error(y_train, y_train_pred),
        'rmse': np.sqrt(mean_squared_error(y_train, y_train_pred)),
        'train_samples': len(y_train)
    }

    metrics_test = {
        'mae': mean_absolute_error(y_test, y_test_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, y_test_pred)),
        'test_samples': len(y_test)
    }

    # Get feature importance
    feature_importance = dict(zip(FEATURE_COLUMNS, model.feature_importances_))

    return {
        'model': model,
        'metrics_train': metrics_train,
        'metrics_test': metrics_test,
        'feature_importance': feature_importance
    }


def save_model(model: LGBMRegressor, path: Path) -> None:
    """
    Save trained LightGBM model to disk

    Args:
        model: Trained LGBMRegressor
        path: Path for save location
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path) -> LGBMRegressor:
    """
    Load trained LightGBM model from disk

    Args:
        path: Path to model file

    Returns:
        Loaded LGBMRegressor
    """
    path = Path(path)
    return joblib.load(path)


def train_and_save_all_lightgbm_models(training_data: pd.DataFrame,
                                        models_dir: str = 'models') -> dict:
    """
    Train and save LightGBM models for all 4 horizons

    Args:
        training_data: Full training dataset
        models_dir: Directory to save models (default 'models/')

    Returns:
        dict with performance metrics for each horizon
    """
    models_path = Path(models_dir)
    models_path.mkdir(parents=True, exist_ok=True)

    results = {}

    for horizon in VALID_HORIZONS:
        print(f"\nTraining LightGBM model for {horizon} horizon...")

        # Train with class weighting
        result = train_lightgbm_model(training_data, horizon)

        # Save model
        model_file = models_path / f'lightgbm_{horizon}.pkl'
        save_model(result['model'], model_file)

        # Store metrics
        results[horizon] = {
            'model_path': str(model_file),
            'train_mae': result['metrics_train']['mae'],
            'train_rmse': result['metrics_train']['rmse'],
            'test_mae': result['metrics_test']['mae'],
            'test_rmse': result['metrics_test']['rmse'],
            'train_samples': result['metrics_train']['train_samples'],
            'test_samples': result['metrics_test']['test_samples'],
            'feature_importance': result['feature_importance']
        }

        print(f"  Train: MAE={result['metrics_train']['mae']:.2f}, "
              f"RMSE={result['metrics_train']['rmse']:.2f}")
        print(f"  Test:  MAE={result['metrics_test']['mae']:.2f}, "
              f"RMSE={result['metrics_test']['rmse']:.2f}")
        print(f"  Saved to: {model_file}")

        # Print top 10 most important features
        top_features = sorted(result['feature_importance'].items(),
                             key=lambda x: x[1], reverse=True)[:10]
        print(f"  Top 10 features:")
        for feat, importance in top_features:
            print(f"    {feat}: {importance:.0f}")

    return results
