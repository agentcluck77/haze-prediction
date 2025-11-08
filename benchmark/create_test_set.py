#!/usr/bin/env python3
"""
Create test dataset from more recent historical data.
This ensures the test set is independent from the training set.
"""

import sys
from pathlib import Path
# Add parent directory to path to import from src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.data_preparation import prepare_training_dataset


def main():
    """Create test set from recent historical data"""
    print("=" * 60)
    print("Creating Test Dataset")
    print("=" * 60)

    # Use more recent data for testing (April-May 2024)
    print("\nFetching test data from 2024-04-01 to 2024-05-31...")

    try:
        test_df = prepare_training_dataset(
            start_date='2024-04-01',
            end_date='2024-05-31',
            sample_hours=24
        )

        if len(test_df) == 0:
            print("✗ No test data created")
            return 1

        print(f"\n✓ Test dataset created: {len(test_df)} samples")
        print(f"  Columns: {list(test_df.columns)}")

        # Save to CSV (in project root data/ directory)
        output_dir = Path(__file__).parent.parent / 'data'
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / 'test_set.csv'
        test_df.to_csv(output_file, index=False)

        print(f"\n✓ Test set saved to: {output_file}")
        print(f"\nTest Set Summary:")
        print(f"  Samples: {len(test_df)}")
        print(f"  Date range: {test_df['timestamp'].min()} to {test_df['timestamp'].max()}")
        print(f"  PSI range (24h): {test_df['actual_psi_24h'].min():.1f} - {test_df['actual_psi_24h'].max():.1f}")

        return 0

    except Exception as e:
        print(f"\n✗ Failed to create test set: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
