"""
Integration tests for live API deployment
Tests against running Docker container at http://localhost:8000

Run with: python3 -m pytest tests/test_live_api_integration.py -v
Or manually: python3 tests/test_live_api_integration.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_endpoint(name, endpoint, expected_fields=None, timeout=10):
    """Test a single endpoint and print results"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Endpoint: GET {endpoint}")
    print(f"{'='*60}")

    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=timeout)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response (formatted):")
            print(json.dumps(data, indent=2))

            if expected_fields:
                missing = [f for f in expected_fields if f not in data]
                if missing:
                    print(f"\n⚠️  Missing expected fields: {missing}")
                else:
                    print(f"\n✓ All expected fields present")

            return True, data
        else:
            print(f"Error Response:")
            print(response.text)
            return False, response.text

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False, str(e)


def run_all_tests():
    """Run all API endpoint tests"""
    results = {}

    # 1. Root endpoint
    success, data = test_endpoint(
        "Root Endpoint",
        "/",
        expected_fields=["message", "version"]
    )
    results["root"] = success

    # 2. Prediction endpoints
    for horizon in ["24h", "48h", "72h", "7d"]:
        success, data = test_endpoint(
            f"Prediction {horizon}",
            f"/predict/{horizon}",
            expected_fields=["prediction", "confidence_interval", "features",
                           "timestamp", "target_timestamp", "horizon"]
        )
        results[f"predict_{horizon}"] = success

    # 3. All predictions (needs longer timeout as it fetches 4 predictions sequentially)
    success, data = test_endpoint(
        "All Predictions",
        "/predict/all",
        expected_fields=["24h", "48h", "72h", "7d"],
        timeout=60
    )
    results["predict_all"] = success

    # 4. Current PSI
    success, data = test_endpoint(
        "Current PSI",
        "/current/psi"
    )
    results["current_psi"] = success

    # 5. Current fires
    success, data = test_endpoint(
        "Current Fires",
        "/current/fires",
        expected_fields=["count", "fires", "timestamp"]
    )
    results["current_fires"] = success

    # 6. Health check
    success, data = test_endpoint(
        "Health Check",
        "/health",
        expected_fields=["status", "last_update", "api_status"]
    )
    results["health"] = success

    # 7. Metrics endpoints
    for horizon in ["24h", "48h", "72h", "7d"]:
        success, data = test_endpoint(
            f"Metrics {horizon}",
            f"/metrics/{horizon}"
        )
        results[f"metrics_{horizon}"] = success

    # Summary
    print(f"\n\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test, success in results.items():
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{status}: {test}")

    print(f"\n{passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    print("Starting Live API Integration Tests")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}\n")

    results = run_all_tests()
