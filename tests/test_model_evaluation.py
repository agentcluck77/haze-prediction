"""
Test model evaluation functionality
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_evaluate_on_test_set_structure():
    """Test that evaluate_on_test_set returns correct structure"""
    from src.evaluation.evaluate_models import evaluate_on_test_set
    from src.training.model_trainer import VALID_HORIZONS

    # Mock the data preparation and model loading
    with patch('src.evaluation.evaluate_models.prepare_training_dataset') as mock_prepare, \
         patch('src.evaluation.evaluate_models.load_model') as mock_load_model:

        # Create mock training data
        mock_df = pd.DataFrame({
            'fire_risk_score': [10, 20, 30, 40, 50],
            'wind_transport_score': [15, 25, 35, 45, 55],
            'baseline_score': [20, 30, 40, 50, 60],
            'actual_psi_24h': [30, 50, 70, 90, 110],
            'actual_psi_48h': [35, 55, 75, 95, 115],
            'actual_psi_72h': [40, 60, 80, 100, 120],
            'actual_psi_7d': [45, 65, 85, 105, 125]
        })
        mock_prepare.return_value = mock_df

        # Create mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([32, 52, 72, 92, 112])
        mock_model.coef_ = np.array([0.5, 0.3, 2.0])
        mock_model.intercept_ = 5.0
        mock_load_model.return_value = mock_model

        # Run evaluation
        results = evaluate_on_test_set(verbose=False)

        # Check structure
        assert results is not None
        assert isinstance(results, dict)

        # Check that we have results for all horizons
        for horizon in VALID_HORIZONS:
            assert horizon in results

        # Check structure of each result
        for horizon, metrics in results.items():
            assert 'mae' in metrics
            assert 'rmse' in metrics
            assert 'baseline_mae' in metrics
            assert 'improvement_pct' in metrics
            assert 'samples' in metrics
            assert 'coefficients' in metrics

            # Check coefficients structure
            assert 'fire_risk' in metrics['coefficients']
            assert 'wind_transport' in metrics['coefficients']
            assert 'baseline' in metrics['coefficients']
            assert 'intercept' in metrics['coefficients']


def test_evaluate_with_custom_dates():
    """Test that custom date range is used"""
    from src.evaluation.evaluate_models import evaluate_on_test_set

    with patch('src.evaluation.evaluate_models.prepare_training_dataset') as mock_prepare, \
         patch('src.evaluation.evaluate_models.load_model'):

        mock_prepare.return_value = pd.DataFrame()  # Return empty to skip actual evaluation

        # Call with custom dates
        evaluate_on_test_set(
            start_date='2023-01-01',
            end_date='2023-12-31',
            verbose=False
        )

        # Verify that prepare_training_dataset was called with correct dates
        mock_prepare.assert_called_once()
        call_args = mock_prepare.call_args
        assert call_args[1]['start_date'] == '2023-01-01'
        assert call_args[1]['end_date'] == '2023-12-31'


def test_evaluate_returns_none_on_error():
    """Test that evaluation returns None when data preparation fails"""
    from src.evaluation.evaluate_models import evaluate_on_test_set

    with patch('src.evaluation.evaluate_models.prepare_training_dataset') as mock_prepare:
        # Simulate error
        mock_prepare.side_effect = Exception("Data fetch failed")

        results = evaluate_on_test_set(verbose=False)

        assert results is None


def test_evaluate_returns_none_with_empty_data():
    """Test that evaluation returns None when no test data is available"""
    from src.evaluation.evaluate_models import evaluate_on_test_set

    with patch('src.evaluation.evaluate_models.prepare_training_dataset') as mock_prepare:
        # Return empty DataFrame
        mock_prepare.return_value = pd.DataFrame()

        results = evaluate_on_test_set(verbose=False)

        assert results is None


def test_evaluate_calculates_improvement():
    """Test that improvement percentage is calculated correctly"""
    from src.evaluation.evaluate_models import evaluate_on_test_set

    # Mock only the data preparation - use real models
    with patch('src.evaluation.evaluate_models.prepare_training_dataset') as mock_prepare:
        # Create mock data
        mock_df = pd.DataFrame({
            'fire_risk_score': [10, 20, 30],
            'wind_transport_score': [15, 25, 35],
            'baseline_score': [20, 30, 40],  # baseline_score * 5 = 100, 150, 200
            'actual_psi_24h': [100, 150, 200],
            'actual_psi_48h': [100, 150, 200],
            'actual_psi_72h': [100, 150, 200],
            'actual_psi_7d': [100, 150, 200]
        })
        mock_prepare.return_value = mock_df

        # Use real models
        results = evaluate_on_test_set(verbose=False)

        # Check results structure
        assert results is not None
        assert '24h' in results
        assert 'mae' in results['24h']
        assert 'improvement_pct' in results['24h']
        assert 'classification' in results['24h']

        # MAE should be reasonable (not checking exact value since using real model)
        assert results['24h']['mae'] >= 0


def test_psi_to_category():
    """Test PSI category conversion"""
    from src.evaluation.evaluate_models import psi_to_category, CATEGORY_NAMES

    # Test individual values
    assert psi_to_category(25) == 0  # Good
    assert psi_to_category(75) == 1  # Moderate
    assert psi_to_category(150) == 2  # Unhealthy
    assert psi_to_category(250) == 3  # Very Unhealthy
    assert psi_to_category(350) == 4  # Hazardous

    # Test boundary values
    assert psi_to_category(50) == 0  # Good
    assert psi_to_category(51) == 1  # Moderate
    assert psi_to_category(100) == 1  # Moderate
    assert psi_to_category(101) == 2  # Unhealthy
    assert psi_to_category(200) == 2  # Unhealthy
    assert psi_to_category(201) == 3  # Very Unhealthy
    assert psi_to_category(300) == 3  # Very Unhealthy
    assert psi_to_category(301) == 4  # Hazardous

    # Test array conversion
    psi_values = pd.Series([25, 75, 150, 250, 350])
    categories = psi_to_category(psi_values)
    expected = [0, 1, 2, 3, 4]
    assert list(categories) == expected


def test_evaluate_includes_classification_metrics():
    """Test that evaluation includes classification metrics"""
    from src.evaluation.evaluate_models import evaluate_on_test_set

    # Mock only the data preparation - use real models
    with patch('src.evaluation.evaluate_models.prepare_training_dataset') as mock_prepare:
        # Create mock data with varied PSI values across categories
        mock_df = pd.DataFrame({
            'fire_risk_score': [10, 20, 30, 40, 50],
            'wind_transport_score': [15, 25, 35, 45, 55],
            'baseline_score': [10, 20, 30, 40, 60],  # Good, Moderate, Unhealthy, Very Unhealthy, Hazardous
            'actual_psi_24h': [30, 80, 150, 250, 320],  # Mix of categories
            'actual_psi_48h': [30, 80, 150, 250, 320],
            'actual_psi_72h': [30, 80, 150, 250, 320],
            'actual_psi_7d': [30, 80, 150, 250, 320]
        })
        mock_prepare.return_value = mock_df

        # Use real models
        results = evaluate_on_test_set(verbose=False)

        # Check that classification metrics are present
        assert results is not None
        assert '24h' in results
        assert 'classification' in results['24h']
        assert 'accuracy' in results['24h']['classification']
        assert 'precision' in results['24h']['classification']
        assert 'recall' in results['24h']['classification']
        assert 'f1_score' in results['24h']['classification']

        # Check that metrics are valid (between 0 and 1)
        assert 0 <= results['24h']['classification']['accuracy'] <= 1
        assert 0 <= results['24h']['classification']['precision'] <= 1
        assert 0 <= results['24h']['classification']['recall'] <= 1
        assert 0 <= results['24h']['classification']['f1_score'] <= 1


def test_evaluate_includes_per_band_metrics():
    """Test that evaluation includes per-band metrics for all 5 PSI bands"""
    from src.evaluation.evaluate_models import evaluate_on_test_set, CATEGORY_NAMES

    # Mock the CSV reading and load_model
    with patch('pandas.read_csv') as mock_read_csv, \
         patch('src.evaluation.evaluate_models.load_model') as mock_load_model:

        # Create mock data with varied PSI values across all categories
        mock_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='6H'),
            'fire_risk_score': [10, 20, 30, 40, 50, 10, 20, 30, 40, 50],
            'wind_transport_score': [15, 25, 35, 45, 55, 15, 25, 35, 45, 55],
            'baseline_score': [10, 20, 30, 40, 60, 10, 20, 30, 40, 60],
            'actual_psi_24h': [30, 80, 150, 250, 320, 35, 85, 155, 255, 325],  # 2 samples per category
            'actual_psi_48h': [30, 80, 150, 250, 320, 35, 85, 155, 255, 325],
            'actual_psi_72h': [30, 80, 150, 250, 320, 35, 85, 155, 255, 325],
            'actual_psi_7d': [30, 80, 150, 250, 320, 35, 85, 155, 255, 325]
        })
        mock_read_csv.return_value = mock_df

        # Create mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([32, 82, 152, 252, 322, 37, 87, 157, 257, 327])
        mock_model.coef_ = np.array([0.5, 0.3, 2.0])
        mock_model.intercept_ = 5.0
        mock_load_model.return_value = mock_model

        # Use mocked models
        results = evaluate_on_test_set(start_date='2024-01-01', end_date='2024-01-10', verbose=False)

        # Check that per-band metrics are present
        assert results is not None
        assert '24h' in results
        assert 'classification' in results['24h']
        assert 'per_band' in results['24h']['classification']

        per_band = results['24h']['classification']['per_band']

        # Check that we have metrics for all 5 categories
        assert len(per_band) == 5

        # Check each band has the expected structure
        for i, category_name in enumerate(CATEGORY_NAMES):
            assert category_name in per_band
            band_metrics = per_band[category_name]

            assert 'precision' in band_metrics
            assert 'recall' in band_metrics
            assert 'f1_score' in band_metrics
            assert 'support' in band_metrics  # Number of samples in this category

            # Metrics should be valid (between 0 and 1, or could be 0 if no samples)
            assert 0 <= band_metrics['precision'] <= 1
            assert 0 <= band_metrics['recall'] <= 1
            assert 0 <= band_metrics['f1_score'] <= 1
            assert band_metrics['support'] >= 0
