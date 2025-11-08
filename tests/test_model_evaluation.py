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

    with patch('src.evaluation.evaluate_models.prepare_training_dataset') as mock_prepare, \
         patch('src.evaluation.evaluate_models.load_model') as mock_load_model:

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

        # Mock model that predicts exactly the actual values
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([100, 150, 200])
        mock_model.coef_ = np.array([0.5, 0.3, 2.0])
        mock_model.intercept_ = 5.0
        mock_load_model.return_value = mock_model

        results = evaluate_on_test_set(verbose=False)

        # When predictions are perfect, MAE should be 0
        # Baseline MAE should be > 0 (since baseline is persistence)
        # Improvement should be very high (close to 100%)
        assert results['24h']['mae'] == 0.0
        assert results['24h']['improvement_pct'] == 100.0
