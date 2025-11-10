#!/usr/bin/env python3
"""
Generate comprehensive evaluation cache file from 2016-02-01 to 2024-12-31
This avoids needing Git LFS files in Cloud Run by pre-computing all evaluation data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.training.data_preparation import prepare_training_dataset
import pandas as pd
from datetime import datetime


def generate_eval_cache():
    """Generate comprehensive evaluation cache file"""

    # Define date range
    start_date = '2014-04-01'
    end_date = '2024-12-31'
    sample_hours = 6  # Sample every 6 hours for reasonable file size

    output_file = Path('data/cache/eval_2014-04-01_2024-12-31_h6.csv')

    print("=" * 70)
    print("Generating Evaluation Cache File")
    print("=" * 70)
    print(f"\nDate range: {start_date} to {end_date}")
    print(f"Sampling: Every {sample_hours} hours")
    print(f"Output: {output_file}")
    print("\nThis will take several minutes...\n")

    try:
        # Generate the dataset
        df = prepare_training_dataset(
            start_date=start_date,
            end_date=end_date,
            sample_hours=sample_hours
        )

        if len(df) == 0:
            print("\nERROR: No data generated!")
            return False

        # Save to cache
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)

        # Print summary
        print("\n" + "=" * 70)
        print("Success!")
        print("=" * 70)
        print(f"\nGenerated {len(df):,} samples")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"Output: {output_file}")

        # Show column info
        print("\nColumns:")
        for col in df.columns:
            non_null = df[col].notna().sum()
            print(f"  {col}: {non_null:,} non-null values")

        # Show sample
        print("\nFirst 5 rows:")
        print(df.head())

        return True

    except Exception as e:
        print(f"\nERROR: Failed to generate cache file: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = generate_eval_cache()
    sys.exit(0 if success else 1)
