"""
Model training module for Linear Regression models
Implements training, evaluation, and persistence for PSI prediction
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error


VALID_HORIZONS = ['24h', '48h', '72h', '7d']
FEATURE_COLUMNS = ['fire_risk_score', 'wind_transport_score', 'baseline_score']
MINIMUM_SAMPLES = 5  # Minimum required for training


def train_model(training_data: pd.DataFrame, horizon: str) -> LinearRegression:
    """
    Train a LinearRegression model for specified horizon

    Args:
        training_data: DataFrame with features and target column
        horizon: One of '24h', '48h', '72h', '7d'

    Returns:
        Trained LinearRegression model

    Raises:
        ValueError: If horizon is invalid or insufficient data
        KeyError: If required columns are missing
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

    # This will raise KeyError if columns are missing
    X = training_data[FEATURE_COLUMNS]
    y = training_data[target_col]

    # Train model
    model = LinearRegression()
    model.fit(X, y)

    return model


def save_model(model: LinearRegression, path: Path) -> None:
    """
    Save trained model to disk using joblib

    Args:
        model: Trained LinearRegression model
        path: Path object or string for save location
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path) -> LinearRegression:
    """
    Load trained model from disk

    Args:
        path: Path object or string to model file

    Returns:
        Loaded LinearRegression model
    """
    path = Path(path)
    return joblib.load(path)


def calculate_metrics(model: LinearRegression, X_test: pd.DataFrame,
                     y_test: pd.Series) -> dict:
    """
    Calculate model performance metrics

    Args:
        model: Trained model
        X_test: Test features
        y_test: Test target values

    Returns:
        dict with 'mae' and 'rmse' keys
    """
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    return {
        'mae': mae,
        'rmse': rmse
    }


def train_all_models(training_data: pd.DataFrame) -> dict:
    """
    Train models for all 4 horizons

    Args:
        training_data: DataFrame with all target columns

    Returns:
        dict mapping horizon -> trained model
    """
    models = {}

    for horizon in VALID_HORIZONS:
        models[horizon] = train_model(training_data, horizon)

    return models


def train_model_with_split(training_data: pd.DataFrame, horizon: str,
                           test_size: float = 0.2, random_state: int = 42) -> dict:
    """
    Train model with train/test split and return metrics for both sets

    Args:
        training_data: Full dataset
        horizon: Prediction horizon
        test_size: Fraction for test set (default 0.2)
        random_state: Random seed for reproducibility

    Returns:
        dict with 'model', 'metrics_train', 'metrics_test' keys
    """
    # Validate horizon
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"Invalid horizon: {horizon}. Must be one of {VALID_HORIZONS}")

    # Extract features and target
    target_col = f'actual_psi_{horizon}'
    X = training_data[FEATURE_COLUMNS]
    y = training_data[target_col]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Train model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Calculate metrics for both sets
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

    return {
        'model': model,
        'metrics_train': metrics_train,
        'metrics_test': metrics_test
    }


def train_and_save_all_models(training_data: pd.DataFrame,
                               models_dir: str = 'models') -> dict:
    """
    Convenience function to train and save all 4 models

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
        print(f"\nTraining model for {horizon} horizon...")

        # Train with split
        result = train_model_with_split(training_data, horizon)

        # Save model
        model_file = models_path / f'linear_regression_{horizon}.pkl'
        save_model(result['model'], model_file)

        # Store metrics
        results[horizon] = {
            'model_path': str(model_file),
            'train_mae': result['metrics_train']['mae'],
            'train_rmse': result['metrics_train']['rmse'],
            'test_mae': result['metrics_test']['mae'],
            'test_rmse': result['metrics_test']['rmse'],
            'train_samples': result['metrics_train']['train_samples'],
            'test_samples': result['metrics_test']['test_samples']
        }

        print(f"  Train: MAE={result['metrics_train']['mae']:.2f}, "
              f"RMSE={result['metrics_train']['rmse']:.2f}")
        print(f"  Test:  MAE={result['metrics_test']['mae']:.2f}, "
              f"RMSE={result['metrics_test']['rmse']:.2f}")
        print(f"  Saved to: {model_file}")

    return results
