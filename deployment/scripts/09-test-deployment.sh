#!/bin/bash
# Test deployed services

set -e

PROJECT_ID="hacx-477608"
REGION="asia-southeast1"

echo "Testing deployed services..."

# Get API URL
API_URL=$(gcloud run services describe haze-prediction-api \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(status.url)")

echo "API URL: ${API_URL}"
echo ""

# Test health endpoint
echo "Testing /health endpoint..."
curl -s ${API_URL}/health | python3 -m json.tool
echo ""

# Test root endpoint
echo "Testing / endpoint..."
curl -s ${API_URL}/ | python3 -m json.tool
echo ""

# Test prediction endpoint
echo "Testing /predict/24h endpoint..."
curl -s ${API_URL}/predict/24h | python3 -m json.tool
echo ""

# Test current PSI
echo "Testing /current/psi endpoint..."
curl -s ${API_URL}/current/psi | python3 -m json.tool
echo ""

# Test current fires
echo "Testing /current/fires endpoint..."
curl -s ${API_URL}/current/fires | python3 -m json.tool
echo ""

echo "All tests completed!"
