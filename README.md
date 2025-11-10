# Singapore Haze Prediction System

Real-time PSI (Pollutant Standards Index) forecasting for Singapore using machine learning.

## Quick Start

### Prerequisites
- Python 3.13+
- Virtual environment at `hacx/`
- Local data files (PSI and VIIRS SNPP fire data)

### 1. Generate Feature Cache

```bash
source hacx/bin/activate
python3 generate_eval_cache.py
```

**Generates cache:** April 2014 - Dec 2024 (sampled every 6h, ~25 features)
- PSI: `data/PSI/Historical24hrPSI.csv`
- Fire: `data/FIRM_MODIS/` (MODIS)
- Weather: `data/weather/era5_grid.csv`

**Output:** `data/cache/eval_2014-04-01_2024-12-31_h6.csv`

**Time:** 10-30 minutes (one-time, reused for both training and evaluation)

### 2. Train Models

```bash
python3 train_models.py
```

**Training data:** April 2014 - Dec 2023 (filtered from cache, 2024 reserved for testing)

**Output:** 4 models saved to `models/` (24h, 48h, 72h, 7d)

**Time:** 1-2 minutes (fast, loads from cache)

### 3. Evaluate Models

```bash
# CLI evaluation (2024 test set)
python3 src/evaluation/evaluate_models.py

# Or via API
curl http://localhost:8000/evaluate
```

**Test set:** Jan 2024 - Dec 2024 (independent from training)

### 4. Start API Server

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
- Fire: MODIS archive (2014-2024, Indonesia + Malaysia + Singapore)
- Weather: ERA5 GRIB (2014-2024, gridded)

**Real-time Predictions (APIs):**
- Fire: VIIRS SNPP NRT (NASA FIRMS, 15min updates)
- Weather: Open-Meteo forecast (hourly updates)
- PSI: NEA Singapore (15min updates)

---

## Model Details

The prediction system uses LightGBM (Light Gradient Boosting Machine), an ensemble of gradient-boosted decision trees optimized for imbalanced regression. Unlike linear models, LightGBM captures non-linear interactions and hierarchical patterns in atmospheric data.

**Algorithm:** LightGBM with Class-Weighted Regression

**Features (25):**
- Fire risk score (1): FRP-weighted composite
- Wind transport score (1): Trajectory simulation
- Baseline score (1): Current PSI / 5.0
- PSI lags (4): 1h, 6h, 12h, 24h ago
- PSI trends (2): Rate of change over 1-6h, 6-24h
- Temporal (5): Hour, day of week, month, day of year, season
- Fire spatial (12): Count, FRP sum/mean by distance band (near/medium/far/very far)

**Horizons:** 24h, 48h, 72h, 7d

**Training:** April 2014 - Dec 2023 (6-hour sampling, includes 2015 haze crisis)
**Test set:** Jan 2024 - Dec 2024 (independent)

### Gradient Boosting Framework

LightGBM builds an ensemble of $M$ sequential decision trees, where each tree corrects the errors of the previous ensemble. The final prediction is:

$$
\hat{y} = F_M(\mathbf{x}) = \sum_{m=1}^{M} \eta \cdot h_m(\mathbf{x})
$$

Where:
- $\mathbf{x} \in \mathbb{R}^{25}$ is the feature vector
- $h_m(\mathbf{x})$ is the $m$-th decision tree (weak learner)
- $\eta = 0.05$ is the learning rate (shrinkage)
- $M = 200$ is the number of boosting iterations

**Gradient Descent in Function Space:**

At iteration $m$, the algorithm fits a tree $h_m$ to the negative gradient of the loss function:

$$
h_m = \arg\min_{h} \sum_{i=1}^{N} w_i \cdot L\left(y_i, F_{m-1}(\mathbf{x}_i) + h(\mathbf{x}_i)\right)
$$

Where:
- $L(y, \hat{y}) = \frac{1}{2}(y - \hat{y})^2$ (L2 loss for regression)
- $w_i$ is the sample weight (class-weighted)
- $F_{m-1}$ is the ensemble after $m-1$ iterations

**Tree Structure:**

Each tree $h_m$ partitions the feature space into $J = 31$ leaf nodes:

$$
h_m(\mathbf{x}) = \sum_{j=1}^{J} \gamma_{mj} \cdot \mathbb{1}(\mathbf{x} \in R_{mj})
$$

Where:
- $R_{mj}$ is the $j$-th leaf region (decision path)
- $\gamma_{mj}$ is the leaf weight (predicted residual)
- $\mathbb{1}(\cdot)$ is the indicator function

### Class Weighting for Imbalanced Regression

Unhealthy PSI events (101-200) are rare (~5% of samples). To prevent the model from ignoring these critical events, we assign higher weights to minority classes.

**Binning Strategy:**

PSI values are discretized into $K=6$ bands:

$$
c_i = \text{bin}(y_i) \in \{0, 1, 2, 3, 4, 5\}
$$

Thresholds: $[0, 50, 100, 200, 300, \infty)$

**Weight Calculation:**

For each class $c$, the weight is inversely proportional to its frequency:

$$
w_c = \frac{N}{K \cdot N_c}
$$

Where:
- $N$ is the total training samples
- $N_c = \sum_{i=1}^{N} \mathbb{1}(c_i = c)$ is the count of class $c$
- $K$ is the number of classes

Sample weight for observation $i$:

$$
w_i = w_{c_i}
$$

**Effect:** Unhealthy PSI samples receive ~4-8× higher weights, forcing the model to prioritize correct predictions for rare but critical events.

### Hyperparameters

**Tree Structure:**
- Max depth: $d = 6$ (prevents overfitting)
- Leaf nodes: $J = 31$ (default for $d=6$)
- Min samples per leaf: $n_{\min} = 20$ (regularization)

**Ensemble:**
- Trees: $M = 200$
- Learning rate: $\eta = 0.05$ (conservative, stable convergence)

**Regularization:**
- L1 penalty: $\alpha = 0.1$ (feature selection)
- L2 penalty: $\lambda = 0.1$ (weight smoothing)
- Subsample ratio: $0.8$ (row sampling per tree)
- Feature fraction: $0.8$ (column sampling per tree)

**Loss Function:**

$$
\mathcal{L} = \sum_{i=1}^{N} w_i \cdot \frac{1}{2}(y_i - \hat{y}_i)^2 + \alpha \sum_{m=1}^{M} \sum_{j=1}^{J} |\gamma_{mj}| + \lambda \sum_{m=1}^{M} \sum_{j=1}^{J} \gamma_{mj}^2
$$

### Training Methodology

**Data Split:** 80% train, 20% validation (stratified by PSI bands)

**Optimization:** Each tree minimizes weighted L2 loss on pseudo-residuals:

$$
r_i^{(m)} = -\frac{\partial L(y_i, F_{m-1}(\mathbf{x}_i))}{\partial F_{m-1}(\mathbf{x}_i)} = y_i - F_{m-1}(\mathbf{x}_i)
$$

**Leaf Weight Update:** For leaf $j$ in tree $m$:

$$
\gamma_{mj} = \frac{\sum_{i \in R_{mj}} w_i \cdot r_i^{(m)}}{\sum_{i \in R_{mj}} w_i + \lambda}
$$

**Convergence:** Model updates stop after $M=200$ iterations (early stopping not used).

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

**4. PSI Historical Features**

- **Lag Features:** PSI values at 1h, 6h, 12h, and 24h before the prediction time, capturing recent air quality history
- **Trend Features:** Rate of change calculated as differences between lags (e.g., $\text{PSI}_{1h} - \text{PSI}_{6h}$), indicating whether air quality is improving or deteriorating

**5. Temporal Features**

Cyclic patterns in haze occurrence:
- Hour of day (0-23)
- Day of week (0-6)
- Month (1-12)
- Day of year (1-365)
- Season (0=SW Monsoon/haze season Jun-Sep, 1=NE Monsoon/wet Dec-Mar, 2=Inter-monsoon)

**6. Fire Spatial Distribution**

Fire activity aggregated by distance bands from Singapore:
- Near (0-250km), Medium (250-500km), Far (500-1000km), Very Far (1000+km)
- For each band: fire count, total FRP, mean FRP

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
