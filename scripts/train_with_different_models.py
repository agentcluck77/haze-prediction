#!/usr/bin/env python3
"""
Example: Train different ML models using the same cached features.
Demonstrates how feature engineering is done once, then reused.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.data_preparation import prepare_training_dataset
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np


def train_and_evaluate(model, model_name, X_train, y_train, X_test, y_test):
    """Train a model and print evaluation metrics"""
    print(f"\nTraining {model_name}...")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"  Test MAE:  {mae:.2f} PSI")
    print(f"  Test RMSE: {rmse:.2f} PSI")

    return {'model': model, 'mae': mae, 'rmse': rmse}


def main():
    print("=" * 60)
    print("Training Multiple Models with Cached Features")
    print("=" * 60)

    # Step 1: Prepare features (this will be FAST after first run - loads from cache)
    print("\n[1/2] Loading training data...")
    training_df = prepare_training_dataset(
        start_date='2014-04-01',
        end_date='2023-12-31',
        sample_hours=6,
        use_cache=True  # Use cached features!
    )

    if len(training_df) == 0:
        print("ERROR: No training data!")
        return 1

    # Step 2: Train multiple models using the SAME features
    print(f"\n[2/2] Training multiple models on {len(training_df)} samples...")

    # Prepare train/test split
    from sklearn.model_selection import train_test_split

    FEATURE_COLUMNS = ['fire_risk_score', 'wind_transport_score', 'baseline_score']
    target_col = 'actual_psi_24h'  # Example: 24h forecast

    X = training_df[FEATURE_COLUMNS]
    y = training_df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"\nTrain samples: {len(X_train)}")
    print(f"Test samples:  {len(X_test)}")

    # Try different models
    models = {
        'Linear Regression': LinearRegression(),
        'Ridge Regression': Ridge(alpha=1.0),
        'Lasso Regression': Lasso(alpha=1.0),
        'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42)
    }

    results = {}
    for name, model in models.items():
        results[name] = train_and_evaluate(model, name, X_train, y_train, X_test, y_test)

    # Summary
    print("\n" + "=" * 60)
    print("Model Comparison")
    print("=" * 60)
    print(f"\n{'Model':<25} {'Test MAE':<12} {'Test RMSE':<12}")
    print("-" * 60)

    for name, result in results.items():
        print(f"{name:<25} {result['mae']:<12.2f} {result['rmse']:<12.2f}")

    # Find best model
    best_model_name = min(results, key=lambda x: results[x]['mae'])
    print(f"\n✓ Best model: {best_model_name} (MAE: {results[best_model_name]['mae']:.2f} PSI)")

    print("\n" + "=" * 60)
    print("Note: All models used the SAME cached features!")
    print("Feature engineering was only done once.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
