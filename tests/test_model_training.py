"""
Test model training functionality
Following TDD protocol: Write tests FIRST, then implementation
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import joblib


def test_train_24h_model():
    """Test training a LinearRegression model for 24h horizon"""
    from src.training.model_trainer import train_model

    # Create sample training data
    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50],
        'wind_transport_score': [15, 25, 35, 45, 55],
        'baseline_score': [20, 30, 40, 50, 60],
        'actual_psi_24h': [30, 50, 70, 90, 110]
    })

    model = train_model(training_data, horizon='24h')

    assert model is not None
    assert hasattr(model, 'predict')
    assert hasattr(model, 'coef_')
    assert hasattr(model, 'intercept_')


def test_train_48h_model():
    """Test training a LinearRegression model for 48h horizon"""
    from src.training.model_trainer import train_model

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50],
        'wind_transport_score': [15, 25, 35, 45, 55],
        'baseline_score': [20, 30, 40, 50, 60],
        'actual_psi_48h': [35, 55, 75, 95, 115]
    })

    model = train_model(training_data, horizon='48h')

    assert model is not None
    assert hasattr(model, 'predict')


def test_train_72h_model():
    """Test training a LinearRegression model for 72h horizon"""
    from src.training.model_trainer import train_model

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50],
        'wind_transport_score': [15, 25, 35, 45, 55],
        'baseline_score': [20, 30, 40, 50, 60],
        'actual_psi_72h': [40, 60, 80, 100, 120]
    })

    model = train_model(training_data, horizon='72h')

    assert model is not None
    assert hasattr(model, 'predict')


def test_train_7d_model():
    """Test training a LinearRegression model for 7d horizon"""
    from src.training.model_trainer import train_model

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50],
        'wind_transport_score': [15, 25, 35, 45, 55],
        'baseline_score': [20, 30, 40, 50, 60],
        'actual_psi_7d': [45, 65, 85, 105, 125]
    })

    model = train_model(training_data, horizon='7d')

    assert model is not None
    assert hasattr(model, 'predict')


def test_train_invalid_horizon():
    """Test that invalid horizon raises ValueError"""
    from src.training.model_trainer import train_model

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30],
        'wind_transport_score': [15, 25, 35],
        'baseline_score': [20, 30, 40],
        'actual_psi_24h': [30, 50, 70]
    })

    with pytest.raises(ValueError, match="Invalid horizon"):
        train_model(training_data, horizon='invalid')


def test_model_prediction():
    """Test that trained model can make predictions"""
    from src.training.model_trainer import train_model

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50, 60, 70, 80],
        'wind_transport_score': [15, 25, 35, 45, 55, 65, 75, 85],
        'baseline_score': [20, 30, 40, 50, 60, 70, 80, 90],
        'actual_psi_24h': [30, 50, 70, 90, 110, 130, 150, 170]
    })

    model = train_model(training_data, horizon='24h')

    # Test prediction
    X_test = pd.DataFrame({
        'fire_risk_score': [25],
        'wind_transport_score': [30],
        'baseline_score': [35]
    })

    prediction = model.predict(X_test)

    assert isinstance(prediction, np.ndarray)
    assert len(prediction) == 1
    assert prediction[0] > 0  # Prediction should be positive


def test_save_model():
    """Test saving a trained model to disk"""
    from src.training.model_trainer import train_model, save_model

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50],
        'wind_transport_score': [15, 25, 35, 45, 55],
        'baseline_score': [20, 30, 40, 50, 60],
        'actual_psi_24h': [30, 50, 70, 90, 110]
    })

    model = train_model(training_data, horizon='24h')

    # Save to temporary path
    test_path = Path('/tmp/test_model_24h.pkl')
    save_model(model, test_path)

    assert test_path.exists()

    # Clean up
    test_path.unlink()


def test_load_model():
    """Test loading a saved model from disk"""
    from src.training.model_trainer import train_model, save_model, load_model

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50],
        'wind_transport_score': [15, 25, 35, 45, 55],
        'baseline_score': [20, 30, 40, 50, 60],
        'actual_psi_24h': [30, 50, 70, 90, 110]
    })

    model = train_model(training_data, horizon='24h')

    # Save and reload
    test_path = Path('/tmp/test_model_24h.pkl')
    save_model(model, test_path)

    loaded_model = load_model(test_path)

    assert loaded_model is not None
    assert hasattr(loaded_model, 'predict')

    # Test that loaded model makes same predictions
    X_test = pd.DataFrame({
        'fire_risk_score': [25],
        'wind_transport_score': [30],
        'baseline_score': [35]
    })

    original_pred = model.predict(X_test)
    loaded_pred = loaded_model.predict(X_test)

    assert np.allclose(original_pred, loaded_pred)

    # Clean up
    test_path.unlink()


def test_calculate_metrics():
    """Test calculating model performance metrics (MAE, RMSE)"""
    from src.training.model_trainer import train_model, calculate_metrics

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        'wind_transport_score': [15, 25, 35, 45, 55, 65, 75, 85, 95, 105],
        'baseline_score': [20, 30, 40, 50, 60, 70, 80, 90, 100, 110],
        'actual_psi_24h': [30, 50, 70, 90, 110, 130, 150, 170, 190, 210]
    })

    model = train_model(training_data, horizon='24h')

    # Create test data
    X_test = training_data[['fire_risk_score', 'wind_transport_score', 'baseline_score']]
    y_test = training_data['actual_psi_24h']

    metrics = calculate_metrics(model, X_test, y_test)

    assert 'mae' in metrics
    assert 'rmse' in metrics
    assert metrics['mae'] >= 0
    assert metrics['rmse'] >= 0
    assert metrics['rmse'] >= metrics['mae']  # RMSE should be >= MAE


def test_train_all_models():
    """Test training all 4 horizon models at once"""
    from src.training.model_trainer import train_all_models

    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        'wind_transport_score': [15, 25, 35, 45, 55, 65, 75, 85, 95, 105],
        'baseline_score': [20, 30, 40, 50, 60, 70, 80, 90, 100, 110],
        'actual_psi_24h': [30, 50, 70, 90, 110, 130, 150, 170, 190, 210],
        'actual_psi_48h': [35, 55, 75, 95, 115, 135, 155, 175, 195, 215],
        'actual_psi_72h': [40, 60, 80, 100, 120, 140, 160, 180, 200, 220],
        'actual_psi_7d': [45, 65, 85, 105, 125, 145, 165, 185, 205, 225]
    })

    models = train_all_models(training_data)

    assert isinstance(models, dict)
    assert '24h' in models
    assert '48h' in models
    assert '72h' in models
    assert '7d' in models

    for horizon, model in models.items():
        assert model is not None
        assert hasattr(model, 'predict')


def test_train_test_split():
    """Test that training uses proper train/test split"""
    from src.training.model_trainer import train_model_with_split

    training_data = pd.DataFrame({
        'fire_risk_score': np.random.rand(100) * 100,
        'wind_transport_score': np.random.rand(100) * 100,
        'baseline_score': np.random.rand(100) * 100,
        'actual_psi_24h': np.random.rand(100) * 200
    })

    result = train_model_with_split(training_data, horizon='24h', test_size=0.2)

    assert 'model' in result
    assert 'metrics_train' in result
    assert 'metrics_test' in result

    # Test set should have ~20% of data
    assert 'test_samples' in result['metrics_test']
    assert result['metrics_test']['test_samples'] == 20  # 20% of 100


def test_insufficient_data():
    """Test that training with insufficient data raises error"""
    from src.training.model_trainer import train_model

    # Only 2 samples - too few for training
    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20],
        'wind_transport_score': [15, 25],
        'baseline_score': [20, 30],
        'actual_psi_24h': [30, 50]
    })

    with pytest.raises(ValueError, match="Insufficient training data"):
        train_model(training_data, horizon='24h')


def test_missing_columns():
    """Test that training with missing columns raises error"""
    from src.training.model_trainer import train_model

    # Missing baseline_score column
    training_data = pd.DataFrame({
        'fire_risk_score': [10, 20, 30, 40, 50],
        'wind_transport_score': [15, 25, 35, 45, 55],
        'actual_psi_24h': [30, 50, 70, 90, 110]
    })

    with pytest.raises(KeyError):
        train_model(training_data, horizon='24h')
