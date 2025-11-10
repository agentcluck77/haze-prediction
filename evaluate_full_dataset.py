#!/usr/bin/env python3
"""
Evaluate models on FULL dataset (2014-2024) to test unhealthy PSI prediction
This includes 2015 haze crisis with 125 unhealthy events
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_recall_fscore_support
import joblib

sys.path.insert(0, str(Path(__file__).parent))

from src.training.lightgbm_trainer import FEATURE_COLUMNS, VALID_HORIZONS


def psi_to_category(psi_value):
    """Convert PSI value to health category"""
    if isinstance(psi_value, (pd.Series, np.ndarray)):
        return pd.cut(
            psi_value,
            bins=[-np.inf, 50, 100, 200, 300, np.inf],
            labels=[0, 1, 2, 3, 4],
            include_lowest=True
        ).astype(int)
    else:
        if psi_value <= 50:
            return 0
        elif psi_value <= 100:
            return 1
        elif psi_value <= 200:
            return 2
        elif psi_value <= 300:
            return 3
        else:
            return 4


CATEGORY_NAMES = ['Good', 'Moderate', 'Unhealthy', 'Very Unhealthy', 'Hazardous']


def main():
    """Evaluate on full dataset including 2015 haze crisis"""
    print("=" * 80)
    print("Full Dataset Evaluation (2014-2024) - Testing Unhealthy PSI Prediction")
    print("=" * 80)

    # Load full dataset
    print("\n[1/2] Loading full dataset (2014-2024)...")
    cache_file = Path('data/cache/eval_2014-04-01_2024-12-31_h6.csv')

    if not cache_file.exists():
        print(f"✗ ERROR: Cache file not found: {cache_file}")
        return 1

    df = pd.read_csv(cache_file, parse_dates=['timestamp'])
    print(f"✓ Loaded {len(df)} samples")

    # Count unhealthy events by year
    df['year'] = df['timestamp'].dt.year
    print("\nUnhealthy PSI events (>100) by year:")
    for year in sorted(df['year'].unique()):
        df_year = df[df['year'] == year]
        unhealthy = (df_year['actual_psi_24h'] > 100).sum()
        very_unhealthy = (df_year['actual_psi_24h'] > 200).sum()
        if unhealthy > 0:
            print(f"  {year}: {unhealthy} unhealthy, {very_unhealthy} very unhealthy")

    # Evaluate models
    print("\n[2/2] Evaluating models on full dataset...")

    for horizon in VALID_HORIZONS:
        print(f"\n{'='*80}")
        print(f"{horizon} Horizon - Full Dataset Metrics")
        print(f"{'='*80}")

        target_col = f'actual_psi_{horizon}'
        y_true = df[target_col]

        # LightGBM
        lgbm_path = Path(f'models/lightgbm_{horizon}.pkl')
        if lgbm_path.exists():
            lgbm_model = joblib.load(lgbm_path)
            X_lgbm = df[FEATURE_COLUMNS]
            y_pred_lgbm = lgbm_model.predict(X_lgbm)

            mae_lgbm = mean_absolute_error(y_true, y_pred_lgbm)
            rmse_lgbm = np.sqrt(mean_squared_error(y_true, y_pred_lgbm))

            y_true_cat = psi_to_category(y_true)
            y_pred_lgbm_cat = psi_to_category(y_pred_lgbm)

            precision, recall, f1, support = precision_recall_fscore_support(
                y_true_cat,
                y_pred_lgbm_cat,
                average=None,
                labels=[0, 1, 2, 3, 4],
                zero_division=0
            )

            print(f"\nLightGBM (25 features + class weighting):")
            print(f"  Overall: MAE={mae_lgbm:.2f}, RMSE={rmse_lgbm:.2f}")
            print(f"\n  Per-Band Metrics:")
            print(f"  {'Band':<20} {'Precision':<12} {'Recall':<12} {'F1':<12} {'Support':<10}")
            print(f"  {'-'*66}")

            for i, name in enumerate(CATEGORY_NAMES):
                print(f"  {name:<20} {precision[i]:<12.3f} {recall[i]:<12.3f} "
                      f"{f1[i]:<12.3f} {support[i]:<10}")

        # LinearRegression
        lr_path = Path(f'models/linear_regression_{horizon}.pkl')
        if lr_path.exists():
            lr_model = joblib.load(lr_path)
            X_lr = df[['fire_risk_score', 'wind_transport_score', 'baseline_score']]
            y_pred_lr = lr_model.predict(X_lr)

            mae_lr = mean_absolute_error(y_true, y_pred_lr)
            rmse_lr = np.sqrt(mean_squared_error(y_true, y_pred_lr))

            y_pred_lr_cat = psi_to_category(y_pred_lr)

            precision_lr, recall_lr, f1_lr, support_lr = precision_recall_fscore_support(
                y_true_cat,
                y_pred_lr_cat,
                average=None,
                labels=[0, 1, 2, 3, 4],
                zero_division=0
            )

            print(f"\nLinearRegression (3 features, no weighting):")
            print(f"  Overall: MAE={mae_lr:.2f}, RMSE={rmse_lr:.2f}")
            print(f"\n  Per-Band Metrics:")
            print(f"  {'Band':<20} {'Precision':<12} {'Recall':<12} {'F1':<12} {'Support':<10}")
            print(f"  {'-'*66}")

            for i, name in enumerate(CATEGORY_NAMES):
                print(f"  {name:<20} {precision_lr[i]:<12.3f} {recall_lr[i]:<12.3f} "
                      f"{f1_lr[i]:<12.3f} {support_lr[i]:<10}")

            # Comparison for Unhealthy band
            print(f"\n  Unhealthy Band (101-200 PSI) Improvement:")
            print(f"  {'Metric':<15} {'LinearRegression':<18} {'LightGBM':<18} {'Improvement':<15}")
            print(f"  {'-'*66}")

            recall_improvement = ((recall[2] - recall_lr[2]) / max(recall_lr[2], 0.001)) * 100
            f1_improvement = ((f1[2] - f1_lr[2]) / max(f1_lr[2], 0.001)) * 100

            print(f"  {'Recall':<15} {recall_lr[2]:<18.3f} {recall[2]:<18.3f} {recall_improvement:>+.1f}%")
            print(f"  {'F1 Score':<15} {f1_lr[2]:<18.3f} {f1[2]:<18.3f} {f1_improvement:>+.1f}%")
            print(f"  {'Support':<15} {support_lr[2]:<18} {support[2]:<18}")

    print("\n" + "=" * 80)
    print("Full dataset evaluation complete!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
