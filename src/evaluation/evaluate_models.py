#!/usr/bin/env python3
"""
Evaluate trained models on 2024 independent test set
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.training.data_preparation import prepare_training_dataset
from src.training.model_trainer import load_model, FEATURE_COLUMNS, VALID_HORIZONS
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
import pandas as pd


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

    # Step 1: Prepare test data
    if verbose:
        print(f"\n[1/2] Preparing test dataset...")

    try:
        test_df = prepare_training_dataset(
            start_date=start_date,
            end_date=end_date,
            sample_hours=sample_hours
        )

        if verbose:
            print(f"✓ Test dataset prepared: {len(test_df)} samples")

        if len(test_df) == 0:
            if verbose:
                print("ERROR: No test samples created!")
            return None

    except Exception as e:
        if verbose:
            print(f"✗ Failed to prepare test data: {e}")
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

            # Calculate metrics
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))

            # Calculate baseline (persistence) for comparison
            baseline_pred = test_df['baseline_score'] * 5.0  # Convert back to PSI
            baseline_mae = mean_absolute_error(y_test, baseline_pred)

            results[horizon] = {
                'mae': float(mae),
                'rmse': float(rmse),
                'baseline_mae': float(baseline_mae),
                'improvement_pct': float((1 - mae/baseline_mae)*100),
                'samples': int(len(y_test)),
                'coefficients': {
                    'fire_risk': float(model.coef_[0]),
                    'wind_transport': float(model.coef_[1]),
                    'baseline': float(model.coef_[2]),
                    'intercept': float(model.intercept_)
                }
            }

            if verbose:
                print(f"  Test MAE: {mae:.2f} PSI")
                print(f"  Test RMSE: {rmse:.2f} PSI")
                print(f"  Baseline MAE: {baseline_mae:.2f} PSI")
                print(f"  Improvement: {baseline_mae - mae:.2f} PSI ({(1 - mae/baseline_mae)*100:.1f}%)")

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
            print(f"\n{'Horizon':<10} {'Test MAE':<12} {'Baseline MAE':<15} {'Improvement':<12} {'Samples':<10}")
            print("-" * 70)

            for horizon in VALID_HORIZONS:
                if horizon in results:
                    r = results[horizon]
                    print(f"{horizon:<10} {r['mae']:<12.2f} {r['baseline_mae']:<15.2f} "
                          f"{r['improvement_pct']:<12.1f}% {r['samples']:<10}")

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

            print("\n" + "=" * 70)

    # Return results dictionary
    return results


def main():
    """CLI entry point"""
    results = evaluate_on_test_set()
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
