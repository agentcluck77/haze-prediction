#!/usr/bin/env python3
"""
Train LightGBM models for PSI prediction
Uses class weighting to handle imbalanced data
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.training.lightgbm_trainer import train_and_save_all_lightgbm_models


def main():
    """Train all LightGBM models and save to models/ directory"""
    print("=" * 60)
    print("Singapore Haze Prediction - LightGBM Training")
    print("=" * 60)

    # Step 1: Load training data from eval cache
    print("\n[1/2] Loading training dataset from eval cache...")

    import pandas as pd

    # Use the comprehensive eval cache (2014-2024) and filter to training period
    eval_cache_file = Path('data/cache/eval_2014-04-01_2024-12-31_h6.csv')

    if not eval_cache_file.exists():
        print(f"\n✗ ERROR: Eval cache not found: {eval_cache_file}")
        print("Please run: python3 generate_eval_cache.py")
        return 1

    print(f"Loading from {eval_cache_file.name}...")
    full_df = pd.read_csv(eval_cache_file)
    full_df['timestamp'] = pd.to_datetime(full_df['timestamp'])

    # Filter to training period (2014-2023, exclude 2024 test set)
    training_df = full_df[
        (full_df['timestamp'] >= '2014-04-01') &
        (full_df['timestamp'] <= '2023-12-31')
    ].copy()

    if len(training_df) == 0:
        print("\n✗ ERROR: No training data in cache!")
        print("Cache may be empty or dates are incorrect.")
        return 1

    print(f"✓ Training dataset prepared: {len(training_df)} samples")
    print(f"  Using 25 features (3 original + 22 new)")

    # Check for missing features
    from src.training.lightgbm_trainer import FEATURE_COLUMNS
    missing_cols = [col for col in FEATURE_COLUMNS if col not in training_df.columns]
    if missing_cols:
        print(f"\n✗ ERROR: Missing feature columns: {missing_cols}")
        print("Available columns:", list(training_df.columns))
        return 1

    # Step 2: Train and save models
    print("\n[2/2] Training LightGBM models with class weighting...")

    try:
        results = train_and_save_all_lightgbm_models(training_df, models_dir='models')

        print("\n" + "=" * 60)
        print("Training Complete!")
        print("=" * 60)

        for horizon, metrics in results.items():
            print(f"\n{horizon} Model:")
            print(f"  Path: {metrics['model_path']}")
            print(f"  Train MAE: {metrics['train_mae']:.2f} PSI")
            print(f"  Train RMSE: {metrics['train_rmse']:.2f} PSI")
            print(f"  Test MAE: {metrics['test_mae']:.2f} PSI")
            print(f"  Test RMSE: {metrics['test_rmse']:.2f} PSI")
            print(f"  Samples: {metrics['train_samples']} train, {metrics['test_samples']} test")

        print("\n" + "=" * 60)
        print("LightGBM models saved to: models/")
        print("Next: Run evaluation to compare with LinearRegression")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n✗ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
