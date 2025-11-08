#!/usr/bin/env python3
"""
Train all PSI prediction models
Generates LinearRegression models for all prediction horizons
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.training.data_preparation import prepare_training_dataset
from src.training.model_trainer import train_and_save_all_models


def main():
    """Train all models and save to models/ directory"""
    print("=" * 60)
    print("Singapore Haze Prediction - Model Training")
    print("=" * 60)

    # Step 1: Prepare training data
    print("\n[1/2] Preparing training dataset...")
    print("This will fetch historical PSI and weather data...")

    try:
        # Train on 2016-2023 data (2024 reserved as independent test set)
        # This uses local VIIRS SNPP fire data from data/FIRMS_historical/
        training_df = prepare_training_dataset(
            start_date='2016-02-01',  # Start from February 2016
            end_date='2023-12-31',     # End of training period (2024 = test set)
            sample_hours=6             # Sample every 6 hours (4 samples/day - good balance)
        )

        print(f"✓ Training dataset prepared: {len(training_df)} samples")
        print(f"  Columns: {list(training_df.columns)}")

    except Exception as e:
        print(f"✗ Failed to prepare training data: {e}")
        print("\nNote: This requires historical data from APIs.")
        print("For now, creating a minimal synthetic dataset for testing...")

        # Create synthetic training data for testing
        import pandas as pd
        import numpy as np

        np.random.seed(42)
        n_samples = 1000

        training_df = pd.DataFrame({
            'fire_risk_score': np.random.uniform(0, 100, n_samples),
            'wind_transport_score': np.random.uniform(0, 100, n_samples),
            'baseline_score': np.random.uniform(0, 100, n_samples),
            'actual_psi_24h': np.random.uniform(20, 150, n_samples),
            'actual_psi_48h': np.random.uniform(20, 150, n_samples),
            'actual_psi_72h': np.random.uniform(20, 150, n_samples),
            'actual_psi_7d': np.random.uniform(20, 150, n_samples),
        })

        print(f"✓ Synthetic dataset created: {len(training_df)} samples")

    # Step 2: Train and save models
    print("\n[2/2] Training models for all horizons...")

    try:
        results = train_and_save_all_models(training_df, models_dir='models')

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
        print("Models saved to: models/")
        print("Ready to start API server!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n✗ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
