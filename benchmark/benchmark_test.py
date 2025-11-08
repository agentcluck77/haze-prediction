#!/usr/bin/env python3
"""
benchmark_test.py

Comprehensive model evaluation immediately after training.
Tests performance on held-out test set before deployment.

Usage:
    # After training Phase 1
    python benchmark_test.py --test-data data/test_set.csv --models models

    # With custom output
    python benchmark_test.py --test-data data/test_set.csv --models models --output reports/benchmark.json
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    precision_recall_fscore_support, confusion_matrix, classification_report
)
import joblib
import json
import os
from pathlib import Path


# PSI Category definitions
PSI_BANDS = {
    'Good': (0, 50),
    'Moderate': (51, 100),
    'Unhealthy': (101, 200),
    'Very Unhealthy': (201, 300),
    'Hazardous': (301, 500)
}

def categorize_psi(psi_value):
    """Assign PSI value to health category"""
    for category, (lower, upper) in PSI_BANDS.items():
        if lower <= psi_value <= upper:
            return category
    return 'Hazardous'  # Anything > 500

class BenchmarkTest:
    """
    Comprehensive model evaluation on held-out test set
    """

    def __init__(self, test_data_path, models_dir):
        self.test_data_path = test_data_path
        self.models_dir = models_dir
        self.results = {}
        self.models = {}

    def load_data(self):
        """Load held-out test set"""
        print(f"Loading test set from {self.test_data_path}...")

        self.test_df = pd.read_csv(self.test_data_path)

        # Expected columns:
        # - Feature columns (fire_risk_score, wind_transport_score, baseline_score)
        # - actual_psi_24h, actual_psi_48h, actual_psi_72h, actual_psi_7d
        # - timestamp (optional, for ordering)

        print(f"✓ Loaded {len(self.test_df)} test samples")
        if 'timestamp' in self.test_df.columns:
            print(f"  Date range: {self.test_df['timestamp'].min()} to {self.test_df['timestamp'].max()}")

        # Add derived columns if timestamp available
        if 'timestamp' in self.test_df.columns:
            self.test_df['timestamp'] = pd.to_datetime(self.test_df['timestamp'])
            self.test_df['month'] = self.test_df['timestamp'].dt.month
            self.test_df['is_dry_season'] = self.test_df['month'].isin([6, 7, 8, 9, 10])

    def load_models(self):
        """Load trained models"""
        print(f"\nLoading models from {self.models_dir}...")

        for horizon in ['24h', '48h', '72h', '7d']:
            # Try loading as .pkl (Phase 1 sklearn)
            pkl_path = os.path.join(self.models_dir, f'linear_regression_{horizon}.pkl')

            if os.path.exists(pkl_path):
                self.models[horizon] = joblib.load(pkl_path)
                print(f"  ✓ {horizon}: Linear Regression (.pkl)")
            else:
                print(f"  ✗ {horizon}: Model not found")

        if not self.models:
            raise FileNotFoundError(f"No models found in {self.models_dir}")

    def predict_all_horizons(self):
        """Generate predictions for all horizons on test set"""
        print(f"\nGenerating predictions on test set...")

        # Identify feature columns
        feature_cols = ['fire_risk_score', 'wind_transport_score', 'baseline_score']

        # Verify feature columns exist
        missing_cols = [col for col in feature_cols if col not in self.test_df.columns]
        if missing_cols:
            raise ValueError(f"Missing feature columns: {missing_cols}")

        X_test = self.test_df[feature_cols]

        # Generate predictions for each horizon
        for horizon in self.models.keys():
            model = self.models[horizon]
            predictions = model.predict(X_test)
            self.test_df[f'predicted_psi_{horizon}'] = predictions

            print(f"  ✓ {horizon}: {len(predictions)} predictions generated")

    def test_regression_metrics(self):
        """Test 1: Regression Performance (MAE, RMSE, R²)"""
        print("\n" + "="*60)
        print("TEST 1: REGRESSION METRICS")
        print("="*60)

        regression_results = {}

        for horizon in self.models.keys():
            y_true = self.test_df[f'actual_psi_{horizon}']
            y_pred = self.test_df[f'predicted_psi_{horizon}']

            mae = mean_absolute_error(y_true, y_pred)
            rmse = np.sqrt(mean_squared_error(y_true, y_pred))
            r2 = r2_score(y_true, y_pred)
            mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100

            # Targets from TDD
            targets = {
                '24h': {'mae': 20, 'rmse': 28},
                '48h': {'mae': 28, 'rmse': 38},
                '72h': {'mae': 38, 'rmse': 50},
                '7d': {'mae': 50, 'rmse': 70}
            }

            target = targets[horizon]
            meets_mae = mae <= target['mae']
            meets_rmse = rmse <= target['rmse']

            regression_results[horizon] = {
                'sample_size': len(y_true),
                'mae': round(mae, 2),
                'rmse': round(rmse, 2),
                'r2': round(r2, 3),
                'mape': round(mape, 2),
                'target_mae': target['mae'],
                'target_rmse': target['rmse'],
                'meets_mae_target': meets_mae,
                'meets_rmse_target': meets_rmse,
                'status': '✓ PASS' if (meets_mae and meets_rmse) else '✗ FAIL'
            }

            print(f"\n{horizon} horizon ({len(y_true)} samples):")
            print(f"  MAE:  {mae:.2f} (target: ≤{target['mae']}) {'✓' if meets_mae else '✗'}")
            print(f"  RMSE: {rmse:.2f} (target: ≤{target['rmse']}) {'✓' if meets_rmse else '✗'}")
            print(f"  R²:   {r2:.3f}")
            print(f"  MAPE: {mape:.2f}%")
            print(f"  Status: {regression_results[horizon]['status']}")

        self.results['regression'] = regression_results

    def test_alert_performance(self):
        """Test 2: Alert System (PSI > 100)"""
        print("\n" + "="*60)
        print("TEST 2: ALERT PERFORMANCE (PSI > 100)")
        print("="*60)

        alert_results = {}

        # Focus on 24h predictions (most critical)
        y_true = self.test_df['actual_psi_24h']
        y_pred = self.test_df['predicted_psi_24h']

        # Binary classification: Alert (>100) vs No Alert (<=100)
        y_true_alert = (y_true > 100).astype(int)
        y_pred_alert = (y_pred > 100).astype(int)

        # Check if there are any positive samples
        if y_true_alert.sum() == 0:
            print("\n  No unhealthy PSI events in test set (all values ≤ 100)")
            print("  Skipping alert performance test")
            alert_results = {
                'sample_size': len(y_true),
                'alert_events': 0,
                'status': 'SKIPPED - No alert events in test set'
            }
        else:
            # Calculate metrics
            precision, recall, f1, support = precision_recall_fscore_support(
                y_true_alert, y_pred_alert, average='binary', zero_division=0
            )

            # Confusion matrix
            tn, fp, fn, tp = confusion_matrix(y_true_alert, y_pred_alert).ravel()

            # Target: >85% precision (from TDD)
            meets_target = precision >= 0.85

            alert_results = {
                'sample_size': len(y_true),
                'alert_events': int(y_true_alert.sum()),
                'predicted_alerts': int(y_pred_alert.sum()),
                'true_positives': int(tp),
                'false_positives': int(fp),
                'true_negatives': int(tn),
                'false_negatives': int(fn),
                'precision': round(precision, 3),
                'recall': round(recall, 3),
                'f1_score': round(f1, 3),
                'target_precision': 0.85,
                'meets_target': meets_target,
                'status': '✓ PASS' if meets_target else '✗ FAIL'
            }

            print(f"\nAlert Classification (24h horizon):")
            print(f"  True Positives:  {tp} (correct alerts)")
            print(f"  False Positives: {fp} (false alarms)")
            print(f"  True Negatives:  {tn} (correct non-alerts)")
            print(f"  False Negatives: {fn} (missed alerts)")
            print(f"\n  Precision: {precision:.1%} (target: ≥85%) {'✓' if meets_target else '✗'}")
            print(f"  Recall:    {recall:.1%}")
            print(f"  F1 Score:  {f1:.3f}")
            print(f"  Status: {alert_results['status']}")

        self.results['alerts'] = alert_results

    def test_seasonal_performance(self):
        """Test 3: Performance by Season"""
        print("\n" + "="*60)
        print("TEST 3: SEASONAL STRATIFICATION")
        print("="*60)

        if 'is_dry_season' not in self.test_df.columns:
            print("\n  No seasonal data available (missing timestamp)")
            self.results['seasonal'] = {'status': 'SKIPPED - No timestamp data'}
            return

        seasonal_results = {}

        for season_name, is_dry in [('Dry Season (Jun-Oct)', True), ('Normal Season', False)]:
            season_mask = self.test_df['is_dry_season'] == is_dry
            season_data = self.test_df[season_mask]

            if len(season_data) == 0:
                continue

            y_true = season_data['actual_psi_24h']
            y_pred = season_data['predicted_psi_24h']

            mae = mean_absolute_error(y_true, y_pred)
            rmse = np.sqrt(mean_squared_error(y_true, y_pred))

            seasonal_results[season_name] = {
                'sample_size': len(season_data),
                'mae': round(mae, 2),
                'rmse': round(rmse, 2),
                'avg_psi': round(y_true.mean(), 1),
                'max_psi': round(y_true.max(), 1)
            }

            print(f"\n{season_name} ({len(season_data)} samples):")
            print(f"  MAE:  {mae:.2f}")
            print(f"  RMSE: {rmse:.2f}")
            print(f"  Avg PSI: {y_true.mean():.1f}")
            print(f"  Max PSI: {y_true.max():.1f}")

        self.results['seasonal'] = seasonal_results


    def generate_summary(self):
        """Generate final benchmark summary"""
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)

        # Count passes/fails
        tests = {}

        # Regression tests
        if '24h' in self.results.get('regression', {}):
            tests['Regression (24h)'] = self.results['regression']['24h']['status']

        # Alert tests
        if 'alerts' in self.results and self.results['alerts'].get('status') != 'SKIPPED - No alert events in test set':
            tests['Alert Performance'] = self.results['alerts']['status']

        passes = sum(1 for status in tests.values() if '✓ PASS' in str(status))
        total = len(tests)

        print(f"\nTest Results: {passes}/{total} PASSED")
        print(f"\nDetailed Status:")
        for test_name, status in tests.items():
            print(f"  {test_name}: {status}")

        # Overall assessment
        overall_pass = passes == total if total > 0 else False

        print(f"\n{'='*60}")
        if overall_pass:
            print("OVERALL ASSESSMENT: ✓ SYSTEM MEETS REQUIREMENTS")
        else:
            print("OVERALL ASSESSMENT: ✗ SYSTEM NEEDS IMPROVEMENT")
        print(f"{'='*60}")

        self.results['summary'] = {
            'tests_passed': passes,
            'tests_total': total,
            'pass_rate': round(passes / total, 2) if total > 0 else 0,
            'overall_pass': overall_pass,
            'timestamp': datetime.now().isoformat(),
            'test_samples': len(self.test_df),
            'models_evaluated': list(self.models.keys())
        }

    def save_report(self, output_file='benchmark_report.json'):
        """Save detailed results to JSON"""

        # Convert numpy types to Python native types for JSON serialization
        def convert_to_serializable(obj):
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            else:
                return obj

        serializable_results = convert_to_serializable(self.results)

        with open(output_file, 'w') as f:
            json.dump(serializable_results, f, indent=2)

        print(f"\n✓ Detailed report saved to: {output_file}")

    def run_all_tests(self, output_file='benchmark_report.json'):
        """Execute complete benchmark suite"""
        print("="*60)
        print("HAZE PREDICTION MODEL - BENCHMARK TEST")
        print(f"Test Data: {self.test_data_path}")
        print(f"Models Dir: {self.models_dir}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        try:
            self.load_data()
            self.load_models()
            self.predict_all_horizons()
            self.test_regression_metrics()
            self.test_alert_performance()
            self.test_seasonal_performance()
            self.generate_summary()

            if output_file:
                self.save_report(output_file)

            return self.results

        except Exception as e:
            print(f"\n✗ BENCHMARK FAILED: {e}")
            import traceback
            traceback.print_exc()
            return None

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Benchmark haze prediction models on held-out test set',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python benchmark_test.py --test-data data/test_set.csv --models models

  # With custom output
  python benchmark_test.py --test-data data/test_set.csv --models models --output reports/results.json
        """
    )
    parser.add_argument('--test-data', type=str, required=True,
                       help='Path to test set CSV file')
    parser.add_argument('--models', type=str, required=True,
                       help='Directory containing trained model files')
    parser.add_argument('--output', type=str, default='benchmark_report.json',
                       help='Output file for detailed report (default: benchmark_report.json)')

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.test_data):
        print(f"✗ Error: Test data file not found: {args.test_data}")
        exit(1)

    if not os.path.exists(args.models):
        print(f"✗ Error: Models directory not found: {args.models}")
        exit(1)

    # Run benchmark
    benchmark = BenchmarkTest(args.test_data, args.models)
    results = benchmark.run_all_tests(args.output)

    if results and results['summary']['overall_pass']:
        print("\n✓ All tests passed - Model approved for deployment!")
        exit(0)  # Success
    else:
        print("\n✗ Some tests failed - Model needs improvement before deployment")
        exit(1)  # Failure
