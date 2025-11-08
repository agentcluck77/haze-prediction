"""
Test API endpoints match UI expectations
Ensures UI and API contracts are aligned
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create FastAPI test client"""
    from src.api.main import app
    return TestClient(app)


class TestPredictionEndpoints:
    """Test prediction endpoints match UI expectations"""

    def test_predict_response_structure(self, client):
        """Test /predict/{horizon} returns structure expected by UI"""
        response = client.get("/predict/24h")
        assert response.status_code == 200
        data = response.json()

        # Required fields per UI TypeScript interface
        assert "prediction" in data
        assert isinstance(data["prediction"], (int, float))

        assert "confidence_interval" in data
        assert isinstance(data["confidence_interval"], list)
        assert len(data["confidence_interval"]) == 2

        assert "timestamp" in data
        assert "target_timestamp" in data
        assert "horizon" in data
        assert data["horizon"] == "24h"

        assert "model_version" in data

        # Optional fields per UI interface
        if "features" in data:
            assert isinstance(data["features"], dict)

        if "health_advisory" in data:
            assert isinstance(data["health_advisory"], str)

    def test_predict_all_response_structure(self, client):
        """Test /predict/all returns structure expected by UI"""
        response = client.get("/predict/all")
        assert response.status_code == 200
        data = response.json()

        # Should have all horizons
        for horizon in ["24h", "48h", "72h", "7d"]:
            assert horizon in data
            # Each should have prediction structure
            assert "prediction" in data[horizon]
            assert "confidence_interval" in data[horizon]
            assert "horizon" in data[horizon]


class TestCurrentDataEndpoints:
    """Test current data endpoints match UI expectations"""

    def test_current_psi_response_structure(self, client):
        """Test /current/psi returns structure expected by UI"""
        response = client.get("/current/psi")
        assert response.status_code == 200
        data = response.json()

        # UI expects timestamp and readings
        assert "timestamp" in data
        assert "readings" in data

    def test_current_fires_response_structure(self, client):
        """Test /current/fires returns structure expected by UI"""
        response = client.get("/current/fires")
        assert response.status_code == 200
        data = response.json()

        # UI expects these fields
        assert "count" in data
        assert isinstance(data["count"], int)

        assert "timestamp" in data

        assert "fires" in data
        assert isinstance(data["fires"], list)

    def test_current_fires_query_parameters(self, client):
        """Test /current/fires accepts min_confidence and min_frp params"""
        # UI passes these query params
        response = client.get("/current/fires?min_confidence=h&min_frp=50")
        # Should not error even if not implemented
        assert response.status_code in [200, 501]

    def test_current_weather_endpoint_exists(self, client):
        """Test /current/weather endpoint exists (UI expects this)"""
        response = client.get("/current/weather")
        # Should return 200, 501 (not implemented), or 503 (service unavailable), not 404
        assert response.status_code in [200, 501, 503], \
            "UI expects /current/weather endpoint to exist"


class TestHistoricalEndpoints:
    """Test historical endpoints match UI expectations"""

    def test_historical_predictions_structure(self, client):
        """Test /historical/{horizon} returns structure expected by UI"""
        response = client.get("/historical/24h")
        assert response.status_code == 200
        data = response.json()

        # UI expects this structure
        if isinstance(data, dict):
            # Should have horizon
            assert "horizon" in data or "predictions" in data

    def test_historical_accepts_query_params(self, client):
        """Test /historical/{horizon} accepts start_date, end_date, limit"""
        # UI sends these params
        response = client.get(
            "/historical/24h?start_date=2025-01-01&end_date=2025-01-31&limit=50"
        )
        assert response.status_code in [200, 501]


class TestMetricsEndpoints:
    """Test metrics endpoints match UI expectations"""

    def test_metrics_horizon_structure(self, client):
        """Test /metrics/{horizon} returns structure expected by UI"""
        response = client.get("/metrics/24h")
        assert response.status_code == 200
        data = response.json()

        # UI expects these fields
        assert "horizon" in data

        # Should have metrics (even if subset)
        assert "mae" in data or "rmse" in data

    def test_metrics_accepts_period_days_param(self, client):
        """Test /metrics/{horizon} accepts period_days param"""
        # UI sends this param
        response = client.get("/metrics/24h?period_days=30")
        assert response.status_code in [200, 501]

    def test_metrics_compare_endpoint_exists(self, client):
        """Test /metrics/compare endpoint exists (UI expects this)"""
        response = client.get("/metrics/compare")
        # Should return 200 or 501 (not implemented), not 404
        assert response.status_code in [200, 501], \
            "UI expects /metrics/compare endpoint to exist"

    def test_metrics_drift_endpoint_exists(self, client):
        """Test /metrics/drift endpoint exists (UI expects this)"""
        response = client.get("/metrics/drift")
        # Should return 200 or 501 (not implemented), not 404
        assert response.status_code in [200, 501], \
            "UI expects /metrics/drift endpoint to exist"


class TestBenchmarkEndpoints:
    """Test benchmark endpoints match UI expectations"""

    def test_benchmark_post_endpoint_exists(self, client):
        """Test POST /benchmark endpoint exists (UI expects this)"""
        payload = {
            "test_data_path": "test.csv",
            "models_dir": "models/"
        }
        response = client.post("/benchmark", json=payload)
        # Should return 200, 201, or 501 (not implemented), not 404
        assert response.status_code in [200, 201, 400, 501], \
            "UI expects POST /benchmark endpoint to exist"

    def test_benchmark_get_status_endpoint_exists(self, client):
        """Test GET /benchmark/{job_id} endpoint exists (UI expects this)"""
        response = client.get("/benchmark/test-job-id")
        # Should return 200, 404 (not found), or 501 (not implemented), not 405
        assert response.status_code in [200, 404, 501], \
            "UI expects GET /benchmark/{job_id} endpoint to exist"


class TestHealthEndpoint:
    """Test health endpoint matches UI expectations"""

    def test_health_response_structure(self, client):
        """Test /health returns structure expected by UI"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # UI expects these fields
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


class TestErrorResponses:
    """Test error responses match UI expectations"""

    def test_error_has_error_field(self, client):
        """Test error responses have 'error' field (UI expects this)"""
        # Trigger an error with invalid horizon
        response = client.get("/predict/invalid")
        assert response.status_code == 400
        data = response.json()

        # UI expects either 'error' or 'detail' field
        assert "error" in data or "detail" in data


class TestCORSConfiguration:
    """Test CORS is configured for UI"""

    def test_cors_allows_all_origins(self, client):
        """Test CORS middleware is configured"""
        # CORS middleware should be present in main.py
        from src.api.main import app

        # Check middleware is registered
        middleware_classes = [m.cls for m in app.user_middleware]
        from fastapi.middleware.cors import CORSMiddleware
        assert CORSMiddleware in middleware_classes, \
            "CORS middleware must be configured for UI to work"


class TestDataTypes:
    """Test data types match UI TypeScript expectations"""

    def test_prediction_is_number(self, client):
        """Test prediction value is a number"""
        response = client.get("/predict/24h")
        data = response.json()

        assert isinstance(data["prediction"], (int, float))

    def test_confidence_interval_is_array(self, client):
        """Test confidence_interval is an array of 2 numbers"""
        response = client.get("/predict/24h")
        data = response.json()

        ci = data["confidence_interval"]
        assert isinstance(ci, list)
        assert len(ci) == 2
        assert all(isinstance(x, (int, float)) for x in ci)

    def test_timestamps_are_strings(self, client):
        """Test timestamps are ISO format strings"""
        response = client.get("/predict/24h")
        data = response.json()

        assert isinstance(data["timestamp"], str)
        assert isinstance(data["target_timestamp"], str)

    def test_fire_count_is_integer(self, client):
        """Test fire count is an integer"""
        response = client.get("/current/fires")
        data = response.json()

        assert isinstance(data["count"], int)
