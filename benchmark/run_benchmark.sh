#!/bin/bash
# Complete benchmark workflow script

set -e  # Exit on error

echo "============================================================"
echo "Singapore Haze Prediction - Benchmark Workflow"
echo "============================================================"

# Activate environment
echo ""
echo "[1/4] Activating environment..."
source hacx/bin/activate

# Train models if needed
if [ ! -f "models/linear_regression_24h.pkl" ]; then
    echo ""
    echo "[2/4] Training models (first time)..."
    python3 train_models.py
else
    echo ""
    echo "[2/4] Models already trained (skipping)"
fi

# Create test dataset
echo ""
echo "[3/4] Creating test dataset..."
python3 benchmark/create_test_set.py

# Run benchmark
echo ""
echo "[4/4] Running benchmark tests..."
python3 benchmark/benchmark_test.py \
    --test-data data/test_set.csv \
    --models models \
    --output benchmark_report.json

echo ""
echo "============================================================"
echo "Benchmark complete! Check benchmark_report.json for details"
echo "============================================================"
