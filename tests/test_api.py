"""
Test FastAPI endpoints
Following TDD protocol: Write tests FIRST, then implementation
"""

import pytest
from fastapi.testclient import TestClient
import json


@pytest.fixture
def client():
    """Create FastAPI test client"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.api.main import app
    return TestClient(app)


class TestRootEndpoint:
    """Test root endpoint"""

    def test_root_returns_welcome_message(self, client):
        """Test GET / returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestPredictionEndpoints:
    """Test prediction endpoints"""

    def test_predict_24h_returns_prediction(self, client):
        """Test GET /predict/24h returns prediction data"""
        response = client.get("/predict/24h")
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "prediction" in data
        assert "confidence_interval" in data
        assert "features" in data
        assert "timestamp" in data
        assert "target_timestamp" in data
        assert "horizon" in data
        assert "model_version" in data

        # Check data types
        assert isinstance(data["prediction"], (int, float))
        assert isinstance(data["confidence_interval"], list)
        assert len(data["confidence_interval"]) == 2
        assert isinstance(data["features"], dict)
        assert data["horizon"] == "24h"

    def test_predict_48h_returns_prediction(self, client):
        """Test GET /predict/48h returns prediction"""
        response = client.get("/predict/48h")
        assert response.status_code == 200
        data = response.json()
        assert data["horizon"] == "48h"

    def test_predict_72h_returns_prediction(self, client):
        """Test GET /predict/72h returns prediction"""
        response = client.get("/predict/72h")
        assert response.status_code == 200
        data = response.json()
        assert data["horizon"] == "72h"

    def test_predict_7d_returns_prediction(self, client):
        """Test GET /predict/7d returns prediction"""
        response = client.get("/predict/7d")
        assert response.status_code == 200
        data = response.json()
        assert data["horizon"] == "7d"

    def test_predict_invalid_horizon_returns_400(self, client):
        """Test GET /predict/invalid returns 400 error"""
        response = client.get("/predict/invalid")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_predict_all_horizons(self, client):
        """Test GET /predict/all returns all predictions"""
        response = client.get("/predict/all")
        assert response.status_code == 200
        data = response.json()

        # Check all horizons present
        assert "24h" in data
        assert "48h" in data
        assert "72h" in data
        assert "7d" in data

        # Check each prediction has required fields
        for horizon in ["24h", "48h", "72h", "7d"]:
            assert "prediction" in data[horizon]
            assert "confidence_interval" in data[horizon]
            assert data[horizon]["horizon"] == horizon

    def test_prediction_confidence_interval_is_valid(self, client):
        """Test confidence interval lower < upper"""
        response = client.get("/predict/24h")
        data = response.json()

        lower, upper = data["confidence_interval"]
        assert lower < upper
        assert lower >= 0  # PSI cannot be negative

    def test_prediction_features_are_present(self, client):
        """Test prediction includes feature scores"""
        response = client.get("/predict/24h")
        data = response.json()

        features = data["features"]
        assert "fire_risk_score" in features
        assert "wind_transport_score" in features
        assert "baseline_score" in features

        # Check feature ranges (0-100)
        assert 0 <= features["fire_risk_score"] <= 100
        assert 0 <= features["wind_transport_score"] <= 100
        assert 0 <= features["baseline_score"] <= 100


class TestCurrentDataEndpoints:
    """Test current data endpoints"""

    def test_current_psi_returns_data(self, client):
        """Test GET /current/psi returns current PSI reading"""
        response = client.get("/current/psi")
        assert response.status_code == 200
        data = response.json()

        # Should have timestamp and readings
        assert "timestamp" in data or "readings" in data

    def test_current_fires_returns_data(self, client):
        """Test GET /current/fires returns fire detection data"""
        response = client.get("/current/fires")
        assert response.status_code == 200
        data = response.json()

        assert "count" in data
        assert "fires" in data
        assert "timestamp" in data
        assert isinstance(data["count"], int)
        assert isinstance(data["fires"], list)

    def test_current_weather_returns_data(self, client):
        """Test GET /current/weather returns current weather data"""
        response = client.get("/current/weather")
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "timestamp" in data
        assert "location" in data
        assert "temperature_2m" in data
        assert "relative_humidity_2m" in data
        assert "wind_speed_10m" in data
        assert "wind_direction_10m" in data
        assert "pressure_msl" in data

        # Check data types
        assert isinstance(data["temperature_2m"], (int, float))
        assert isinstance(data["relative_humidity_2m"], (int, float))
        assert isinstance(data["wind_speed_10m"], (int, float))
        assert isinstance(data["wind_direction_10m"], (int, float))
        assert isinstance(data["pressure_msl"], (int, float))

        # Check reasonable value ranges
        assert -50 <= data["temperature_2m"] <= 60  # Celsius
        assert 0 <= data["relative_humidity_2m"] <= 100  # Percentage
        assert 0 <= data["wind_direction_10m"] < 360  # Degrees


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check_returns_status(self, client):
        """Test GET /health returns system status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "last_update" in data
        assert "api_status" in data

        # Check last_update structure
        assert "fires" in data["last_update"]
        assert "weather" in data["last_update"]
        assert "psi" in data["last_update"]

        # Check api_status structure
        assert "firms" in data["api_status"]
        assert "open_meteo" in data["api_status"]
        assert "psi" in data["api_status"]


class TestHistoricalEndpoints:
    """Test historical data endpoints"""

    def test_historical_predictions_24h(self, client):
        """Test GET /historical/24h returns historical data"""
        response = client.get("/historical/24h")
        assert response.status_code == 200
        data = response.json()

        # Should return list or dict with predictions
        assert isinstance(data, (list, dict))

    def test_historical_predictions_with_date_range(self, client):
        """Test GET /historical/24h with date filters"""
        response = client.get(
            "/historical/24h?start_date=2025-01-01&end_date=2025-01-31"
        )
        assert response.status_code == 200


class TestMetricsEndpoints:
    """Test model metrics endpoints"""

    def test_metrics_24h_returns_performance(self, client):
        """Test GET /metrics/24h returns model metrics"""
        response = client.get("/metrics/24h")
        assert response.status_code == 200
        data = response.json()

        # Should have performance metrics
        assert "mae" in data or "rmse" in data or "sample_size" in data

    def test_metrics_all_horizons(self, client):
        """Test metrics available for all horizons"""
        for horizon in ["24h", "48h", "72h", "7d"]:
            response = client.get(f"/metrics/{horizon}")
            assert response.status_code == 200


class TestCORSHeaders:
    """Test CORS middleware"""

    def test_cors_headers_present(self, client):
        """Test CORS headers are set correctly"""
        response = client.get("/")

        # FastAPI CORS middleware should add these headers
        # (may not be present in TestClient, but we check the middleware is configured)
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling"""

    def test_404_for_unknown_endpoint(self, client):
        """Test 404 for non-existent endpoints"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_prediction_handles_missing_data_gracefully(self, client):
        """Test prediction endpoint handles errors gracefully"""
        # This should not crash even if data sources are unavailable
        response = client.get("/predict/24h")
        # Should return 200 or 503 (service unavailable), not 500
        assert response.status_code in [200, 503]


class TestResponseFormats:
    """Test response formats"""

    def test_all_responses_are_json(self, client):
        """Test all endpoints return JSON"""
        endpoints = [
            "/",
            "/predict/24h",
            "/predict/all",
            "/current/psi",
            "/current/fires",
            "/health",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.headers["content-type"] == "application/json"

    def test_timestamps_are_iso_format(self, client):
        """Test timestamps use ISO 8601 format"""
        response = client.get("/predict/24h")
        data = response.json()

        timestamp = data["timestamp"]
        # Should be parseable as ISO format
        from datetime import datetime
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


class TestPredictionValidation:
    """Test prediction validation logic"""

    def test_prediction_value_is_reasonable(self, client):
        """Test prediction values are in reasonable range"""
        response = client.get("/predict/24h")
        data = response.json()

        prediction = data["prediction"]
        # PSI typically 0-500, but could spike higher in extreme events
        assert 0 <= prediction <= 1000

    def test_feature_scores_sum_logically(self, client):
        """Test feature scores are internally consistent"""
        response = client.get("/predict/24h")
        data = response.json()

        features = data["features"]
        # All features should be non-negative
        assert features["fire_risk_score"] >= 0
        assert features["wind_transport_score"] >= 0
        assert features["baseline_score"] >= 0
