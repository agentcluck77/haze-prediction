#!/bin/bash
# Quick start script for Docker deployment

set -e

echo "============================================================"
echo "Singapore Haze Prediction - Docker Deployment"
echo "============================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "✗ Error: Docker is not running"
    echo "  Please start Docker Desktop and try again"
    exit 1
fi

echo ""
echo "[1/5] Checking prerequisites..."

# Check if models exist
if [ ! -f "models/linear_regression_24h.pkl" ]; then
    echo "✗ Models not found"
    echo "  Training models first..."
    source hacx/bin/activate
    python3 train_models.py
else
    echo "✓ Models found"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "[2/5] Creating .env file..."
    cp .env.example .env
    echo "✓ Created .env (using defaults)"
    echo "  Note: Edit .env to customize configuration"
else
    echo ""
    echo "[2/5] Environment configuration"
    echo "✓ .env file exists"
fi

# Create directories
echo ""
echo "[3/5] Creating directories..."
mkdir -p data logs
echo "✓ Created data/ and logs/ directories"

# Build containers
echo ""
echo "[4/5] Building Docker containers..."
docker-compose build
echo "✓ Containers built"

# Start services
echo ""
echo "[5/5] Starting services..."
docker-compose up -d

echo ""
echo "============================================================"
echo "Waiting for services to be healthy..."
echo "============================================================"

# Wait for services
sleep 5

# Check health
echo ""
echo "Checking service health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ API failed to start"
        echo "  Check logs: docker-compose logs api"
        exit 1
    fi
    sleep 2
done

# Check UI health
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✓ UI is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠ UI failed to start (this is optional)"
        echo "  Check logs: docker-compose logs ui"
    fi
    sleep 2
done

echo ""
echo "============================================================"
echo "Deployment Complete!"
echo "============================================================"
echo ""
echo "Services running:"
echo "  UI:        http://localhost:3000"
echo "  API:       http://localhost:8000"
echo "  Docs:      http://localhost:8000/docs"
echo "  Database:  localhost:5432"
echo ""
echo "Quick commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Stop:         docker-compose down"
echo "  Restart:      docker-compose restart"
echo ""
echo "Test the services:"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:8000/predict/24h"
echo "  Open http://localhost:3000 in your browser"
echo "============================================================"
