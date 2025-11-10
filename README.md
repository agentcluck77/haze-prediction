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

The prediction system uses a multiple linear regression model to forecast the Pollutant Standards Index (PSI). This model establishes a linear relationship between a set of independent features and the dependent variable (the future PSI value).

**Algorithm:** Linear Regression

**Features (3):**
- Fire risk score (0-100): FRP, distance, recency
- Wind transport score (0-100): Trajectory simulation
- Baseline score (0-100): Current PSI / 5.0

**Horizons:** 24h, 48h, 72h, 7d

**Training:** Mar 2016 - Dec 2023 (hourly sampling)
**Test set:** Jan 2024 - Dec 2024 (independent)

### How it Works

At its core, the model calculates the predicted PSI as a weighted sum of its input features. The relationship is expressed by the following equation:

$$
\text{Predicted PSI} = \beta_0 + \beta_1 \times \text{FireRisk} + \beta_2 \times \text{WindTransport} + \beta_3 \times \text{Baseline} + \epsilon
$$

Where:
-   `Predicted PSI` is the forecasted PSI value.
-   `FireRisk`, `WindTransport`, and `Baseline` are the input feature scores.
-   $\beta_0$ is the model's intercept, representing the baseline PSI prediction when all feature scores are zero.
-   $\beta_1, \beta_2, \beta_3$ are the coefficients (weights) learned by the model during training. Each coefficient represents the impact of its corresponding feature on the final PSI prediction.
-   $\epsilon$ represents the model's error term, accounting for variability not captured by the features.

During training, the model learns the optimal values for the coefficients ($\beta_i$) that minimize the difference between its predictions and the actual historical PSI values. A separate model with a unique set of coefficients is trained for each prediction horizon.

#### Feature Calculation

The input features are engineered to capture different aspects of haze formation and transport.

**1. Fire Risk Score**

This score quantifies the threat from regional fire hotspots. For each hotspot $i$, a contribution is calculated based on its intensity (FRP), distance, and recency.

-   **Intensity Weight ($W_{\text{intensity}}$):** Normalizes the Fire Radiative Power (FRP).
    $$ W_{\text{intensity}, i} = \min\left(\frac{\text{FRP}_i}{100}, 1.0\right) $$
-   **Distance Weight ($W_{\text{distance}}$):** Exponentially decays with distance from Singapore.
    $$ W_{\text{distance}, i} = \exp\left(-\frac{\text{distance}_i \text{ (km)}}{1000}\right) $$
-   **Recency Weight ($W_{\text{recency}}$):** Exponentially decays with the age of the fire detection.
    $$ W_{\text{recency}, i} = \exp\left(-\frac{\text{age\_in\_hours}_i}{24}\right) $$

The final score is the scaled sum of contributions from all $N$ fires, with a constant wind favorability factor of 0.5.

$$ \text{FireRiskScore} = \min\left(10 \times \sum_{i=1}^{N} (W_{\text{intensity}, i} \cdot W_{\text{distance}, i} \cdot W_{\text{recency}, i} \cdot 0.5), 100\right) $$

**2. Wind Transport Score**

This score models the likelihood of smoke being transported to Singapore. It involves a multi-step simulation:

1.  **Fire Clustering:** Nearby fires are grouped into $M$ clusters using the DBSCAN algorithm.
2.  **Trajectory Simulation:** For each cluster $j$, a smoke trajectory is simulated based on hourly wind forecasts.
3.  **Proximity Score ($P_j$):** The minimum distance ($d_{\min, j}$) of each trajectory to Singapore is calculated. A score is assigned based on this proximity:
    $$ P_j = \begin{cases} 100 & \text{if } d_{\min, j} < 50 \text{ km} \\ 100 \times \left(1 - \frac{d_{\min, j} - 50}{150}\right) & \text{if } 50 \le d_{\min, j} < 200 \text{ km} \\ 0 & \text{if } d_{\min, j} \ge 200 \text{ km} \end{cases} $$
4.  **Final Score:** The total score is the sum of proximity scores weighted by each cluster's total FRP, capped at 100.
    $$ \text{WindTransportScore} = \min\left(\sum_{j=1}^{M} P_j \times \frac{\text{FRP}_{\text{cluster}, j}}{1000}, 100\right) $$

**3. Baseline Score**

This score represents the current air quality situation, providing a starting point for the forecast. It is calculated by normalizing the current PSI value to a 0-100 scale.

$$ \text{BaselineScore} = \frac{\min(\text{Current PSI}, 500)}{5.0} $$

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
