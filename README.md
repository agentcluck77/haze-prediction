# Singapore Haze Prediction System

Real-time PSI (Pollutant Standards Index) forecasting for Singapore using machine learning.

## Quick Start

### Prerequisites
- Python 3.13+
- Virtual environment at `hacx/`
- Local data files (PSI and VIIRS SNPP fire data)

### 1. Train Models

```bash
source hacx/bin/activate
python3 train_models.py
```

**Training data:** March 2016 - Dec 2023 (loaded from local files)
- PSI: `data/PSI/Historical24hrPSI.csv`
- Fire: `data/FIRMS_historical/` (VIIRS SNPP)
- Weather: Open-Meteo ERA5 archive (API)

**Output:** 4 models saved to `models/` (24h, 48h, 72h, 7d)

**Time:** 2-4 hours for full training

### 2. Evaluate Models

```bash
# CLI evaluation (2024 test set)
python3 src/evaluation/evaluate_models.py

# Or via API
curl http://localhost:8000/evaluate
```

**Test set:** Jan 2024 - Dec 2024 (independent from training)

### 3. Start API Server

```bash
source hacx/bin/activate
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

---

## API Endpoints

### Predictions
```bash
curl http://localhost:8000/predict/24h      # Single horizon
curl http://localhost:8000/predict/all       # All horizons
```

### Evaluation
```bash
# Default: 2024 test set
curl http://localhost:8000/evaluate

# Custom period
curl "http://localhost:8000/evaluate?start_date=2023-01-01&end_date=2023-12-31"
```

### Current Data
```bash
curl http://localhost:8000/current/psi      # Latest PSI
curl http://localhost:8000/current/fires    # Active fires
```

### System
```bash
curl http://localhost:8000/health           # Health check
curl http://localhost:8000/metrics/24h      # Model metrics
```

---

## Testing

```bash
source hacx/bin/activate
pytest tests/ -v
```

---

## Project Structure

```
hacx-extra/
├── src/
│   ├── data_ingestion/    # API clients (FIRMS, Open-Meteo, NEA)
│   ├── features/          # Feature engineering (fire, wind, baseline)
│   ├── training/          # Model training & data loaders
│   ├── evaluation/        # Model evaluation
│   ├── api/               # FastAPI application
│   └── scheduler/         # APScheduler tasks
├── data/
│   ├── PSI/              # Historical PSI data (2014-2025)
│   └── FIRMS_historical/ # VIIRS SNPP fire data (2016-2024)
├── models/               # Trained models (.pkl files)
├── tests/                # Test suite
├── APIs/                 # OpenAPI specification
├── train_models.py       # Training script
└── README.md
```

---

## Data Sources

**Training (Local Files):**
- PSI: Historical24hrPSI.csv (2014-2025, all regions)
- Fire: VIIRS SNPP archive (2016-2024, Indonesia + Malaysia)
- Weather: Open-Meteo ERA5 (2016-2024, API)

**Real-time Predictions (APIs):**
- Fire: VIIRS SNPP NRT (NASA FIRMS, 15min updates)
- Weather: Open-Meteo forecast (hourly updates)
- PSI: NEA Singapore (15min updates)

---

## Model Details

**Algorithm:** Linear Regression

**Features (3):**
- Fire risk score (0-100): FRP, distance, recency
- Wind transport score (0-100): Trajectory simulation
- Baseline score (0-100): Current PSI / 5.0

**Horizons:** 24h, 48h, 72h, 7d

**Training:** Mar 2016 - Dec 2023 (hourly sampling)
**Test set:** Jan 2024 - Dec 2024 (independent)

---

## Docker Deployment

```bash
# Quick start
./docker-start.sh

# Or manually
docker-compose up -d
curl http://localhost:8000/health
```

See `DOCKER.md` for details.

---

## Troubleshooting

**Model not found:**
```bash
python3 train_models.py
```

**API not responding:**
```bash
curl http://localhost:8000/health
```

**Docker issues:**
```bash
docker-compose logs -f
docker-compose down -v && docker-compose up -d
```

---

## License

MIT
