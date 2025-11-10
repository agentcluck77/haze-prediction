#!/usr/bin/env python3
"""
Evaluate LightGBM models on 2024 test set and compare with LinearRegression
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, precision_recall_fscore_support
import joblib

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.training.lightgbm_trainer import FEATURE_COLUMNS, VALID_HORIZONS


def psi_to_category(psi_value):
    """Convert PSI value to health category (0-4)"""
    if isinstance(psi_value, (pd.Series, np.ndarray)):
        return pd.cut(
            psi_value,
            bins=[-np.inf, 50, 100, 200, 300, np.inf],
            labels=[0, 1, 2, 3, 4],
            include_lowest=True
        ).astype(int)
    else:
        if psi_value <= 50:
            return 0  # Good
        elif psi_value <= 100:
            return 1  # Moderate
        elif psi_value <= 200:
            return 2  # Unhealthy
        elif psi_value <= 300:
            return 3  # Very Unhealthy
        else:
            return 4  # Hazardous


CATEGORY_NAMES = ['Good', 'Moderate', 'Unhealthy', 'Very Unhealthy', 'Hazardous']


def evaluate_model(model, X_test, y_test, model_name):
    """Evaluate a single model and return detailed metrics"""
    # Make predictions
    y_pred = model.predict(X_test)

    # Regression metrics
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    # Classification metrics
    y_test_cat = psi_to_category(y_test)
    y_pred_cat = psi_to_category(y_pred)

    # Per-band metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test_cat,
        y_pred_cat,
        average=None,
        labels=[0, 1, 2, 3, 4],
        zero_division=0
    )

    # Overall metrics
    precision_avg, recall_avg, f1_avg, _ = precision_recall_fscore_support(
        y_test_cat,
        y_pred_cat,
        average='weighted',
        zero_division=0
    )

    per_band = {}
    for i, category_name in enumerate(CATEGORY_NAMES):
        per_band[category_name] = {
            'precision': float(precision[i]),
            'recall': float(recall[i]),
            'f1_score': float(f1[i]),
            'support': int(support[i])
        }

    return {
        'model_name': model_name,
        'mae': float(mae),
        'rmse': float(rmse),
        'r2': float(r2),
        'precision': float(precision_avg),
        'recall': float(recall_avg),
        'f1_score': float(f1_avg),
        'per_band': per_band
    }


def main():
    """Evaluate LightGBM and LinearRegression models on 2024 test set"""
    print("=" * 70)
    print("LightGBM vs LinearRegression - Model Comparison")
    print("=" * 70)

    # Load test data
    print("\n[1/3] Loading 2024 test dataset...")
    cache_file = Path('data/cache/eval_2014-04-01_2024-12-31_h6.csv')

    if not cache_file.exists():
        print(f"✗ ERROR: Cache file not found: {cache_file}")
        return 1

    df = pd.read_csv(cache_file, parse_dates=['timestamp'])
    test_df = df[(df['timestamp'] >= '2024-01-01') & (df['timestamp'] <= '2024-12-31')]

    print(f"✓ Loaded {len(test_df)} test samples")

    # Check for LightGBM features
    missing_lgbm_cols = [col for col in FEATURE_COLUMNS if col not in test_df.columns]
    if missing_lgbm_cols:
        print(f"✗ ERROR: Missing LightGBM feature columns: {missing_lgbm_cols}")
        return 1

    # Evaluate all models
    print("\n[2/3] Evaluating models...")

    results = {}

    for horizon in VALID_HORIZONS:
        print(f"\nEvaluating {horizon} horizon...")

        target_col = f'actual_psi_{horizon}'
        y_test = test_df[target_col]

        # Evaluate LightGBM
        lgbm_path = Path(f'models/lightgbm_{horizon}.pkl')
        if lgbm_path.exists():
            lgbm_model = joblib.load(lgbm_path)
            X_test_lgbm = test_df[FEATURE_COLUMNS]
            lgbm_results = evaluate_model(lgbm_model, X_test_lgbm, y_test, 'LightGBM')
            print(f"  LightGBM: MAE={lgbm_results['mae']:.2f}, F1={lgbm_results['f1_score']:.3f}")
        else:
            lgbm_results = None
            print(f"  LightGBM: Model not found")

        # Evaluate LinearRegression
        lr_path = Path(f'models/linear_regression_{horizon}.pkl')
        if lr_path.exists():
            lr_model = joblib.load(lr_path)
            # LinearRegression uses only 3 features
            X_test_lr = test_df[['fire_risk_score', 'wind_transport_score', 'baseline_score']]
            lr_results = evaluate_model(lr_model, X_test_lr, y_test, 'LinearRegression')
            print(f"  LinearRegression: MAE={lr_results['mae']:.2f}, F1={lr_results['f1_score']:.3f}")
        else:
            lr_results = None
            print(f"  LinearRegression: Model not found")

        results[horizon] = {
            'lightgbm': lgbm_results,
            'linear_regression': lr_results
        }

    # Print comparison
    print("\n[3/3] Model Comparison")
    print("=" * 70)

    for horizon in VALID_HORIZONS:
        lgbm = results[horizon]['lightgbm']
        lr = results[horizon]['linear_regression']

        if not lgbm or not lr:
            continue

        print(f"\n{horizon} Horizon:")
        print(f"{'Metric':<20} {'LightGBM':<15} {'LinearRegression':<15} {'Improvement':<15}")
        print("-" * 70)

        mae_improvement = ((lr['mae'] - lgbm['mae']) / lr['mae']) * 100
        rmse_improvement = ((lr['rmse'] - lgbm['rmse']) / lr['rmse']) * 100
        f1_improvement = ((lgbm['f1_score'] - lr['f1_score']) / lr['f1_score']) * 100

        print(f"{'MAE':<20} {lgbm['mae']:<15.2f} {lr['mae']:<15.2f} {mae_improvement:>+.1f}%")
        print(f"{'RMSE':<20} {lgbm['rmse']:<15.2f} {lr['rmse']:<15.2f} {rmse_improvement:>+.1f}%")
        print(f"{'F1 Score':<20} {lgbm['f1_score']:<15.3f} {lr['f1_score']:<15.3f} {f1_improvement:>+.1f}%")

        # Per-band comparison for Unhealthy category
        print(f"\n  Unhealthy Band (101-200 PSI) Comparison:")
        print(f"  {'Metric':<15} {'LightGBM':<15} {'LinearRegression':<15}")
        print(f"  {'-'*45}")

        lgbm_unhealthy = lgbm['per_band']['Unhealthy']
        lr_unhealthy = lr['per_band']['Unhealthy']

        print(f"  {'Precision':<15} {lgbm_unhealthy['precision']:<15.3f} {lr_unhealthy['precision']:<15.3f}")
        print(f"  {'Recall':<15} {lgbm_unhealthy['recall']:<15.3f} {lr_unhealthy['recall']:<15.3f}")
        print(f"  {'F1 Score':<15} {lgbm_unhealthy['f1_score']:<15.3f} {lr_unhealthy['f1_score']:<15.3f}")
        print(f"  {'Support':<15} {lgbm_unhealthy['support']:<15} {lr_unhealthy['support']:<15}")

    print("\n" + "=" * 70)
    print("Evaluation complete!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
