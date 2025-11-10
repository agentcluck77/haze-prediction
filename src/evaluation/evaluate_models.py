#!/usr/bin/env python3
"""
Evaluate trained models on 2024 independent test set
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.training.model_trainer import load_model, FEATURE_COLUMNS, VALID_HORIZONS
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score, precision_recall_fscore_support
import pandas as pd


def psi_to_category(psi_value):
    """
    Convert PSI value to health category

    Categories based on Singapore NEA standards:
    - 0-50: Good
    - 51-100: Moderate
    - 101-200: Unhealthy
    - 201-300: Very Unhealthy
    - 301+: Hazardous

    Args:
        psi_value: PSI value (float or array)

    Returns:
        int or array: Category index (0-4)
    """
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


def evaluate_on_test_set(start_date='2024-01-01', end_date='2024-12-31', sample_hours=1, verbose=True):
    """
    Evaluate models on independent test set

    Args:
        start_date: Start date for test set (YYYY-MM-DD)
        end_date: End date for test set (YYYY-MM-DD)
        sample_hours: Sampling frequency in hours (default: 1 = hourly)
        verbose: Print detailed output (default: True)

    Returns:
        dict: Evaluation results for all horizons
    """
    if verbose:
        print("=" * 70)
        print(f"Model Evaluation - Test Set ({start_date} to {end_date})")
        print("=" * 70)

    # Step 1: Load test data from cache
    if verbose:
        print(f"\n[1/2] Loading test dataset from cache...")

    try:
        # Use pre-generated cache file (covers 2014-04-01 to 2024-12-31, sampled every 6 hours)
        cache_file = Path('data/cache/eval_2014-04-01_2024-12-31_h6.csv')

        if not cache_file.exists():
            raise FileNotFoundError(f"Evaluation cache file not found: {cache_file}")

        # Load cache and filter to requested date range
        test_df = pd.read_csv(cache_file, parse_dates=['timestamp'])

        # Filter to date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        test_df = test_df[(test_df['timestamp'] >= start_dt) & (test_df['timestamp'] <= end_dt)]

        # Resample if needed (cache is sampled at 6 hours)
        if sample_hours != 6:
            if verbose:
                print(f"Note: Cache is sampled at 6 hours, requested {sample_hours} hours. Using cache sampling.")

        if verbose:
            print(f"✓ Test dataset loaded: {len(test_df)} samples from cache")

        if len(test_df) == 0:
            if verbose:
                print("ERROR: No test samples in date range!")
            return None

    except Exception as e:
        if verbose:
            print(f"✗ Failed to load test data: {e}")
            import traceback
            traceback.print_exc()
        return None

    # Step 2: Evaluate each model
    if verbose:
        print("\n[2/2] Evaluating models on test data...")

    models_dir = Path('models')
    results = {}

    for horizon in VALID_HORIZONS:
        if verbose:
            print(f"\nEvaluating {horizon} model...")

        model_file = models_dir / f'linear_regression_{horizon}.pkl'

        if not model_file.exists():
            if verbose:
                print(f"  ERROR: Model not found: {model_file}")
            continue

        try:
            # Load model
            model = load_model(model_file)

            # Prepare test data
            target_col = f'actual_psi_{horizon}'
            X_test = test_df[FEATURE_COLUMNS]
            y_test = test_df[target_col]

            # Make predictions
            y_pred = model.predict(X_test)

            # Calculate regression metrics
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)

            # Calculate MAPE (Mean Absolute Percentage Error)
            # Avoid division by zero - only calculate for non-zero actual values
            non_zero_mask = y_test != 0
            if non_zero_mask.sum() > 0:
                mape = np.mean(np.abs((y_test[non_zero_mask] - y_pred[non_zero_mask]) / y_test[non_zero_mask])) * 100
            else:
                mape = 0.0

            # Calculate baseline (persistence) for comparison
            baseline_pred = test_df['baseline_score'] * 5.0  # Convert back to PSI
            baseline_mae = mean_absolute_error(y_test, baseline_pred)

            # Calculate classification metrics (PSI categories)
            y_test_cat = psi_to_category(y_test)
            y_pred_cat = psi_to_category(y_pred)

            accuracy = accuracy_score(y_test_cat, y_pred_cat)

            # Calculate weighted average metrics
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test_cat,
                y_pred_cat,
                average='weighted',
                zero_division=0
            )

            # Calculate per-class metrics for all 5 PSI bands
            precision_per_class, recall_per_class, f1_per_class, support_per_class = precision_recall_fscore_support(
                y_test_cat,
                y_pred_cat,
                average=None,  # Get per-class metrics
                labels=[0, 1, 2, 3, 4],  # Ensure we get metrics for all 5 classes
                zero_division=0
            )

            # Create per-band dictionary
            per_band = {}
            for i, category_name in enumerate(CATEGORY_NAMES):
                per_band[category_name] = {
                    'precision': float(precision_per_class[i]),
                    'recall': float(recall_per_class[i]),
                    'f1_score': float(f1_per_class[i]),
                    'support': int(support_per_class[i])  # Number of actual samples in this category
                }

            # Calculate improvement percentage (handle division by zero)
            if baseline_mae > 0:
                improvement_pct = float((1 - mae/baseline_mae)*100)
            else:
                improvement_pct = 0.0

            results[horizon] = {
                'mae': float(mae),
                'rmse': float(rmse),
                'r2': float(r2),
                'mape': float(mape),
                'baseline_mae': float(baseline_mae),
                'improvement_pct': improvement_pct,
                'samples': int(len(y_test)),
                'coefficients': {
                    'fire_risk': float(model.coef_[0]),
                    'wind_transport': float(model.coef_[1]),
                    'baseline': float(model.coef_[2]),
                    'intercept': float(model.intercept_)
                },
                'classification': {
                    'accuracy': float(accuracy),
                    'precision': float(precision),
                    'recall': float(recall),
                    'f1_score': float(f1),
                    'per_band': per_band
                }
            }

            if verbose:
                print(f"  Test MAE: {mae:.2f} PSI")
                print(f"  Test RMSE: {rmse:.2f} PSI")
                print(f"  Baseline MAE: {baseline_mae:.2f} PSI")
                print(f"  Improvement: {baseline_mae - mae:.2f} PSI ({(1 - mae/baseline_mae)*100:.1f}%)")
                print(f"  Classification Accuracy: {accuracy*100:.1f}%")
                print(f"  F1 Score: {f1:.3f}")

        except Exception as e:
            if verbose:
                print(f"  ERROR evaluating model: {e}")
                import traceback
                traceback.print_exc()

    # Step 3: Summary (only if verbose)
    if verbose:
        print("\n" + "=" * 70)
        print(f"Evaluation Summary ({start_date} to {end_date})")
        print("=" * 70)

        if len(results) == 0:
            print("\nNo models evaluated successfully!")
        else:
            # Create summary table
            print(f"\n{'Horizon':<10} {'Test MAE':<12} {'Baseline MAE':<15} {'Improvement':<12} {'Accuracy':<12} {'F1 Score':<12} {'Samples':<10}")
            print("-" * 90)

            for horizon in VALID_HORIZONS:
                if horizon in results:
                    r = results[horizon]
                    print(f"{horizon:<10} {r['mae']:<12.2f} {r['baseline_mae']:<15.2f} "
                          f"{r['improvement_pct']:<12.1f}% {r['classification']['accuracy']*100:<12.1f}% "
                          f"{r['classification']['f1_score']:<12.3f} {r['samples']:<10}")

            # Print model coefficients
            print("\n" + "=" * 70)
            print("Model Coefficients")
            print("=" * 70)

            for horizon in VALID_HORIZONS:
                if horizon in results:
                    r = results[horizon]
                    coef = r['coefficients']
                    print(f"\n{horizon} Model:")
                    print(f"  Fire risk coefficient:      {coef['fire_risk']:>8.4f}")
                    print(f"  Wind transport coefficient: {coef['wind_transport']:>8.4f}")
                    print(f"  Baseline coefficient:       {coef['baseline']:>8.4f}")
                    print(f"  Intercept:                  {coef['intercept']:>8.4f}")

            # Check if fire features are being used
            print("\n" + "=" * 70)
            print("Fire Feature Usage Analysis")
            print("=" * 70)

            any_fire_used = False
            for horizon in VALID_HORIZONS:
                if horizon in results:
                    fire_coef = results[horizon]['coefficients']['fire_risk']
                    wind_coef = results[horizon]['coefficients']['wind_transport']

                    if abs(fire_coef) > 0.01 or abs(wind_coef) > 0.01:
                        any_fire_used = True
                        print(f"\n{horizon}: Fire features ARE being used")
                        print(f"  Fire risk impact: {fire_coef:.4f} per unit")
                        print(f"  Wind transport impact: {wind_coef:.4f} per unit")
                    else:
                        print(f"\n{horizon}: Fire features NOT being used (coefficients near 0)")

            if not any_fire_used:
                print("\nWARNING: No models are using fire features!")
                print("This suggests the model is relying only on persistence (baseline).")

            # Print per-band metrics
            print("\n" + "=" * 70)
            print("Per-Band Classification Metrics")
            print("=" * 70)

            for horizon in VALID_HORIZONS:
                if horizon in results:
                    print(f"\n{horizon} Model:")
                    print(f"{'Band':<20} {'Precision':<12} {'Recall':<12} {'F1 Score':<12} {'Support':<12}")
                    print("-" * 68)
                    per_band = results[horizon]['classification']['per_band']
                    for band_name, metrics in per_band.items():
                        print(f"{band_name:<20} {metrics['precision']:<12.3f} {metrics['recall']:<12.3f} "
                              f"{metrics['f1_score']:<12.3f} {metrics['support']:<12}")

            print("\n" + "=" * 70)

    # Return results dictionary
    return results


def main():
    """CLI entry point"""
    results = evaluate_on_test_set()
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
