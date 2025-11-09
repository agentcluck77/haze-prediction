# Singapore Haze Prediction Dashboard

A comprehensive web-based dashboard for the Singapore Haze Prediction API, built based on the OpenAPI specification.

## Features

### Overview Tab
- **Current PSI**: Real-time PSI readings with regional breakdown
- **Predictions Summary**: Quick view of predictions across all horizons (24h, 48h, 72h, 7d)
- **Active Fires**: Fire detection summary from NASA FIRMS
- **Weather Conditions**: Current weather data from Open-Meteo

### Predictions Tab
- View PSI predictions for specific time horizons
- Confidence intervals and feature contributions
- SHAP explanations (for Phase 2 XGBoost model)
- Health advisories based on predicted PSI

### Current Data Tab
- **PSI Readings**: Detailed regional PSI, PM2.5, and PM10 readings
- **Fire Detections**: Filterable list of active fires with location, FRP, and confidence
- **Weather Data**: Comprehensive weather conditions

### Historical Tab
- Historical predictions with validation
- Interactive charts comparing predicted vs actual PSI
- Filterable by date range and horizon
- Error analysis and model performance tracking

### Metrics Tab
- **Model Performance**: MAE, RMSE, R², MAPE metrics
- **Alert Metrics**: Precision, recall, F1 score for PSI alerts
- **Model Drift**: Detection of performance degradation over time
- **Compare Horizons**: Side-by-side comparison across prediction horizons

### Benchmark Tab
- Start comprehensive model benchmarks
- Track benchmark job progress in real-time
- View detailed benchmark results including:
  - Regression metrics per horizon
  - Alert classification performance
  - Category accuracy
  - Seasonal performance
  - Calibration analysis

## Setup

### Option 1: Simple HTTP Server

1. Navigate to the `ui` directory:
```bash
cd ui
```

2. Start a simple HTTP server (Python 3):
```bash
python3 -m http.server 8080
```

3. Open your browser and navigate to:
```
http://localhost:8080/dashboard.html
```

### Option 2: Using Node.js http-server

1. Install http-server globally:
```bash
npm install -g http-server
```

2. Navigate to the `ui` directory and start the server:
```bash
cd ui
http-server -p 8080
```

3. Open your browser and navigate to:
```
http://localhost:8080/dashboard.html
```

### Option 3: Serve with Flask/Backend

If you have a Flask backend, you can serve the dashboard from there:

```python
from flask import Flask, send_from_directory

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('ui', 'dashboard.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('ui', path)
```

## Configuration

### API Server Selection

The dashboard supports multiple API servers:
- **Local Development**: `http://localhost:8000`
- **Staging**: `https://staging-api.hazeprediction.sg/v1`
- **Production**: `https://api.hazeprediction.sg/v1`

Select your server from the dropdown in the header. The dashboard will automatically use the selected server for all API calls.

## Usage

### Viewing Predictions

1. Click on the **Predictions** tab
2. Select a time horizon (24h, 48h, 72h, 7d, or All)
3. View prediction details including:
   - Predicted PSI value
   - Confidence interval
   - Contributing features
   - SHAP explanations (if available)
   - Health advisory

### Monitoring Current Conditions

1. Click on the **Current Data** tab
2. View real-time PSI readings, fire detections, and weather data
3. Filter fires by confidence level and minimum FRP

### Analyzing Historical Performance

1. Click on the **Historical** tab
2. Select a horizon and date range
3. View interactive charts and detailed tables
4. Analyze prediction accuracy over time

### Running Benchmarks

1. Click on the **Benchmark** tab
2. Enter the test data path and models directory
3. Optionally specify a model version
4. Click "Start Benchmark"
5. Monitor progress in real-time
6. View detailed results when complete

## API Endpoints Used

The dashboard integrates with all endpoints defined in the OpenAPI specification:

- `GET /predict/{horizon}` - Get prediction for specific horizon
- `GET /predict/all` - Get all predictions
- `GET /current/psi` - Current PSI readings
- `GET /current/fires` - Active fire detections
- `GET /current/weather` - Current weather conditions
- `GET /historical/{horizon}` - Historical predictions
- `GET /metrics/{horizon}` - Model performance metrics
- `GET /metrics/compare` - Compare metrics across horizons
- `GET /metrics/drift` - Model drift analysis
- `POST /benchmark` - Start benchmark job
- `GET /benchmark/{job_id}` - Get benchmark status
- `GET /health` - System health check

## Features

- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Real-time Updates**: Auto-refreshes data every 5 minutes
- **Error Handling**: Graceful error messages and retry logic
- **Loading States**: Visual feedback during API calls
- **Interactive Charts**: Powered by Chart.js
- **Modern UI**: Clean, professional design with smooth animations

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Troubleshooting

### CORS Issues

If you encounter CORS errors, ensure your API server has CORS enabled:

```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
```

### API Connection Errors

1. Check that the API server is running
2. Verify the server URL in the dropdown
3. Check browser console for detailed error messages
4. Ensure the API endpoints match the OpenAPI specification

### Charts Not Displaying

1. Ensure Chart.js is loaded (check browser console)
2. Verify data is being returned from the API
3. Check that the canvas elements exist in the DOM

## Development

### File Structure

```
ui/
├── dashboard.html    # Main HTML structure
├── styles.css        # All styling
├── api.js           # API client
├── dashboard.js     # Dashboard logic and UI interactions
└── README.md        # This file
```

### Customization

- **Colors**: Modify CSS variables in `styles.css` (`:root` section)
- **API Base URL**: Change default in `api.js` constructor
- **Auto-refresh Interval**: Modify interval in `dashboard.js` (currently 300000ms = 5 minutes)

## License

MIT License - See main project license

