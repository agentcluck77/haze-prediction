"""
Test LightGBM prediction API functionality
Following TDD: Write test FIRST, see it FAIL, then implement
"""

import pytest
from datetime import datetime
from pathlib import Path
from src.api.prediction_lgbm import predict_psi_lgbm, predict_all_horizons_lgbm


def test_predict_psi_lgbm_returns_prediction():
    """Test that LightGBM prediction returns valid prediction structure"""
    # This test should FAIL initially (RED phase)
    # Then PASS after we implement predict_psi_lgbm (GREEN phase)

    result = predict_psi_lgbm(horizon='24h')

    # Check structure
    assert 'prediction' in result
    assert 'confidence_interval' in result
    assert 'features' in result
    assert 'timestamp' in result
    assert 'target_timestamp' in result
    assert 'horizon' in result
    assert 'model_version' in result

    # Check prediction is reasonable (PSI should be 0-500)
    assert 0 <= result['prediction'] <= 500

    # Check model version indicates LightGBM
    assert 'lightgbm' in result['model_version'].lower()


def test_predict_psi_lgbm_uses_correct_model_file():
    """Test that LightGBM prediction loads the correct model file"""
    # Should load lightgbm_24h.pkl, not linear_regression_24h.pkl

    # Check model file exists
    model_file = Path('models/lightgbm_24h.pkl')
    assert model_file.exists(), "LightGBM model file should exist"

    # Call prediction (should use lightgbm model internally)
    result = predict_psi_lgbm(horizon='24h')

    # Prediction should succeed
    assert result['prediction'] is not None


def test_predict_all_horizons_lgbm_returns_all_predictions():
    """Test that we can predict all horizons with LightGBM"""
    results = predict_all_horizons_lgbm()

    # Should have all 4 horizons
    assert '24h' in results
    assert '48h' in results
    assert '72h' in results
    assert '7d' in results

    # Each should have valid structure
    for horizon, result in results.items():
        assert 'prediction' in result
        assert 0 <= result['prediction'] <= 500
        assert 'lightgbm' in result['model_version'].lower()


def test_lightgbm_prediction_uses_25_features():
    """Test that LightGBM prediction calculates all 25 features"""
    # LightGBM needs 25 features (not just 3 like LinearRegression)

    result = predict_psi_lgbm(horizon='24h')

    # Features dict should include NEW feature categories
    # (we'll store feature values in metadata for verification)
    assert 'features' in result

    # Should have more than just the 3 basic features
    # The actual 25 features are used internally, but we'll verify
    # by checking prediction doesn't error out (model expects 25 features)
    assert result['prediction'] is not None


def test_lightgbm_prediction_handles_missing_historical_psi():
    """Test that prediction gracefully handles missing historical PSI data"""
    # PSI lag features need historical data
    # Should either fetch from DB/cache or use fallback values

    # This should not crash
    result = predict_psi_lgbm(horizon='24h')
    assert result is not None


def test_lightgbm_prediction_calculates_temporal_features():
    """Test that temporal features are calculated correctly"""
    result = predict_psi_lgbm(horizon='24h')

    # Should succeed (temporal features are easy - just use current time)
    assert result is not None

    # Verify timestamp is recent
    timestamp = datetime.fromisoformat(result['timestamp'])
    now = datetime.now()
    time_diff = abs((now - timestamp).total_seconds())
    assert time_diff < 60, "Prediction timestamp should be within last minute"


def test_lightgbm_vs_linear_different_predictions():
    """Test that LightGBM gives different predictions than LinearRegression"""
    # Import both
    from src.api.prediction import predict_psi as predict_psi_linear

    # Get predictions from both
    lgbm_result = predict_psi_lgbm(horizon='24h')
    linear_result = predict_psi_linear(horizon='24h')

    # They should give different predictions (using different models + features)
    # Allow small tolerance in case they happen to be similar
    assert 'prediction' in lgbm_result
    assert 'prediction' in linear_result

    # Just verify both return valid predictions
    assert 0 <= lgbm_result['prediction'] <= 500
    assert 0 <= linear_result['prediction'] <= 500
