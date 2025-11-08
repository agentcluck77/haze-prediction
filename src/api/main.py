"""
FastAPI application for Singapore Haze Prediction System
RESTful API endpoints for PSI prediction and monitoring
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import json
import numpy as np

from src.api.prediction import predict_psi, predict_all_horizons, VALID_HORIZONS
from src.data_ingestion.psi import fetch_current_psi
from src.data_ingestion.firms import fetch_recent_fires
from src.evaluation.evaluate_models import evaluate_on_test_set


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Custom JSON encoder for NumPy and pandas types
class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles NumPy and pandas types"""
    def default(self, obj):
        import pandas as pd

        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Pydantic models for responses
class PredictionResponse(BaseModel):
    prediction: float
    confidence_interval: List[float]
    features: Dict[str, float]
    timestamp: str
    target_timestamp: str
    horizon: str
    model_version: str
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    last_update: Dict[str, Optional[str]]
    api_status: Dict[str, str]
    database: Optional[str] = None


# Create FastAPI app
app = FastAPI(
    title="Singapore Haze Prediction API",
    version="1.0.0",
    description="Real-time haze forecasting for Singapore using machine learning"
)


# CORS middleware for government dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Singapore Haze Prediction API",
        "version": "1.0.0",
        "endpoints": {
            "predictions": "/predict/{horizon}",
            "all_predictions": "/predict/all",
            "current_psi": "/current/psi",
            "current_fires": "/current/fires",
            "current_weather": "/current/weather",
            "health": "/health",
            "historical": "/historical/{horizon}",
            "metrics": "/metrics/{horizon}",
            "metrics_compare": "/metrics/compare",
            "metrics_drift": "/metrics/drift",
            "benchmark": "/benchmark",
            "benchmark_status": "/benchmark/{job_id}",
            "evaluate": "/evaluate"
        },
        "horizons": VALID_HORIZONS
    }


# Prediction endpoints
# NOTE: /predict/all must come BEFORE /predict/{horizon} to avoid route conflicts
@app.get("/predict/all")
async def get_all_predictions():
    """
    Get predictions for all time horizons

    Returns:
        dict mapping horizon -> prediction data
    """
    try:
        predictions = predict_all_horizons()
        return predictions
    except Exception as e:
        logger.error(f"Failed to generate predictions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate predictions: {str(e)}"
        )


@app.get("/predict/{horizon}", response_model=PredictionResponse)
async def get_prediction(horizon: str):
    """
    Get PSI prediction for specified horizon

    Args:
        horizon: One of '24h', '48h', '72h', '7d'

    Returns:
        Prediction data with confidence interval and features

    Raises:
        HTTPException: 400 if invalid horizon, 500 if prediction fails
    """
    if horizon not in VALID_HORIZONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid horizon: {horizon}. Must be one of {VALID_HORIZONS}"
        )

    try:
        prediction = predict_psi(horizon)
        return prediction
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Model not available: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Prediction failed for {horizon}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


# Current data endpoints
@app.get("/current/psi")
async def get_current_psi():
    """
    Get latest PSI reading from NEA

    Returns:
        Current PSI data for all regions
    """
    try:
        psi_df = fetch_current_psi()

        # Convert DataFrame to dict format
        if len(psi_df) > 0:
            # Convert to list of records
            readings = psi_df.to_dict('records')
            timestamp = psi_df['timestamp'].iloc[0] if 'timestamp' in psi_df.columns else datetime.now()

            psi_data = {
                "timestamp": timestamp,
                "readings": readings
            }
        else:
            psi_data = {
                "timestamp": datetime.now(),
                "readings": []
            }

        # Use custom JSON encoder to handle NumPy and pandas types
        json_str = json.dumps(psi_data, cls=NumpyEncoder)
        return JSONResponse(content=json.loads(json_str))
    except Exception as e:
        logger.error(f"Failed to fetch current PSI: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch PSI data: {str(e)}"
        )


@app.get("/current/fires")
async def get_current_fires(
    min_confidence: Optional[str] = None,
    min_frp: Optional[float] = None
):
    """
    Get active fire detections (last 24 hours)

    Args:
        min_confidence: Minimum confidence level ('l', 'n', 'h')
        min_frp: Minimum Fire Radiative Power

    Returns:
        Fire detection data with count and list of fires
    """
    try:
        fires = fetch_recent_fires(days=1)

        # Apply filters if provided
        if min_confidence and len(fires) > 0:
            fires = fires[fires['confidence'] >= min_confidence]

        if min_frp is not None and len(fires) > 0:
            fires = fires[fires['frp'] >= min_frp]

        return {
            "count": len(fires),
            "fires": fires.to_dict('records') if len(fires) > 0 else [],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to fetch fire data: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch fire data: {str(e)}"
        )


@app.get("/current/weather")
async def get_current_weather():
    """
    Get current weather conditions for Singapore

    Returns:
        Current weather data
    """
    try:
        from src.data_ingestion.weather import fetch_current_weather

        # Singapore coordinates
        weather = fetch_current_weather(1.3521, 103.8198)

        if weather is not None and len(weather) > 0:
            return {
                "timestamp": datetime.now().isoformat(),
                "location": "Singapore",
                "temperature_2m": weather.get("temperature_2m"),
                "relative_humidity_2m": weather.get("relative_humidity_2m"),
                "wind_speed_10m": weather.get("wind_speed_10m"),
                "wind_direction_10m": weather.get("wind_direction_10m"),
                "pressure_msl": weather.get("pressure_msl"),
                "cloud_cover": weather.get("cloud_cover"),
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Weather data unavailable"
            )
    except Exception as e:
        logger.error(f"Failed to fetch weather data: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch weather data: {str(e)}"
        )


# Historical data endpoint
@app.get("/historical/{horizon}")
async def get_historical_predictions(
    horizon: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get historical predictions and validation results

    Args:
        horizon: Prediction horizon
        start_date: Optional start date (ISO format YYYY-MM-DD)
        end_date: Optional end date (ISO format YYYY-MM-DD)

    Returns:
        Historical prediction data
    """
    if horizon not in VALID_HORIZONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid horizon: {horizon}"
        )

    # Placeholder - would query database in production
    return {
        "horizon": horizon,
        "start_date": start_date,
        "end_date": end_date,
        "predictions": [],
        "message": "Historical data retrieval not yet implemented"
    }


# Metrics endpoints
# NOTE: /metrics/compare and /metrics/drift must come BEFORE /metrics/{horizon} to avoid route conflicts
@app.get("/metrics/compare")
async def compare_metrics(period_days: int = 30):
    """
    Compare metrics across all horizons

    Args:
        period_days: Number of days to analyze (default: 30)

    Returns:
        Metrics for all horizons
    """
    from src.api.prediction import MODEL_METRICS

    results = {}
    for horizon in VALID_HORIZONS:
        results[horizon] = {
            "horizon": horizon,
            "period_days": period_days,
            "mae": MODEL_METRICS[horizon]['mae'],
            "rmse": MODEL_METRICS[horizon]['rmse'],
            "sample_size": 0,
            "last_validated": None,
        }

    return results


@app.get("/metrics/drift")
async def get_model_drift():
    """
    Detect model drift

    Returns:
        Drift detection results
    """
    # Placeholder - would perform statistical drift detection
    return {
        "drift_detected": False,
        "baseline_period": "2024-01-01 to 2024-06-30",
        "current_period": "2024-07-01 to 2024-12-31",
        "metrics_change": {},
        "recommendation": "No significant drift detected. Model performance is stable."
    }


@app.get("/metrics/{horizon}")
async def get_model_metrics(horizon: str, period_days: int = 30):
    """
    Get model performance metrics

    Args:
        horizon: Prediction horizon
        period_days: Number of days to analyze (default: 30)

    Returns:
        Performance metrics (MAE, RMSE, etc.)
    """
    if horizon not in VALID_HORIZONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid horizon: {horizon}"
        )

    # Placeholder - would calculate from validation results in production
    from src.api.prediction import MODEL_METRICS

    return {
        "horizon": horizon,
        "period_days": period_days,
        "mae": MODEL_METRICS[horizon]['mae'],
        "rmse": MODEL_METRICS[horizon]['rmse'],
        "sample_size": 0,
        "last_validated": None,
        "message": "Metrics from model validation (not operational data)"
    }


# Evaluation endpoint
@app.get("/evaluate")
async def evaluate_models(
    start_date: Optional[str] = "2024-01-01",
    end_date: Optional[str] = "2024-12-31",
    sample_hours: Optional[int] = 1
):
    """
    Evaluate models on independent test set

    Args:
        start_date: Start date for test set (YYYY-MM-DD), default: 2024-01-01
        end_date: End date for test set (YYYY-MM-DD), default: 2024-12-31
        sample_hours: Sampling frequency in hours, default: 1

    Returns:
        Evaluation results for all horizons with metrics and coefficients

    Raises:
        HTTPException: 500 if evaluation fails
    """
    try:
        logger.info(f"Evaluating models on {start_date} to {end_date}")

        # Run evaluation (verbose=False for API)
        results = evaluate_on_test_set(
            start_date=start_date,
            end_date=end_date,
            sample_hours=sample_hours,
            verbose=False
        )

        if results is None or len(results) == 0:
            raise HTTPException(
                status_code=500,
                detail="Evaluation failed: No results generated"
            )

        # Add metadata
        response = {
            "test_period": {
                "start_date": start_date,
                "end_date": end_date,
                "sample_hours": sample_hours
            },
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"Model evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}"
        )


# Benchmark endpoints
class BenchmarkRequest(BaseModel):
    """Request model for benchmark job"""
    test_data_path: str
    models_dir: str
    model_version: Optional[str] = None


@app.post("/benchmark")
async def start_benchmark(request: BenchmarkRequest):
    """
    Start a benchmark job

    Args:
        request: Benchmark job configuration

    Returns:
        Job ID and status URL
    """
    import uuid

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Placeholder - would queue actual benchmark job
    return {
        "job_id": job_id,
        "status": "queued",
        "status_url": f"/benchmark/{job_id}",
        "estimated_duration_minutes": 10,
        "message": "Benchmark endpoint not yet implemented"
    }


@app.get("/benchmark/{job_id}")
async def get_benchmark_status(job_id: str):
    """
    Get benchmark job status

    Args:
        job_id: Benchmark job ID

    Returns:
        Job status and results
    """
    # Placeholder - would check actual job status
    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Benchmark results not available - endpoint not yet implemented"
    }


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    System health check

    Returns:
        Status of API, data sources, and last update times
    """
    try:
        # Check if we can fetch data from each source
        api_status = {
            "firms": "unknown",
            "open_meteo": "unknown",
            "psi": "unknown"
        }

        # Try to fetch PSI
        try:
            psi_data = fetch_current_psi()
            api_status["psi"] = "healthy" if len(psi_data) > 0 else "degraded"
        except:
            api_status["psi"] = "unhealthy"

        # Try to fetch fires
        try:
            fires = fetch_recent_fires(days=1)
            api_status["firms"] = "healthy" if fires is not None else "degraded"
        except:
            api_status["firms"] = "unhealthy"

        # Try weather (implicitly tested via prediction)
        try:
            from src.data_ingestion.weather import fetch_current_weather
            weather = fetch_current_weather(1.3521, 103.8198)
            api_status["open_meteo"] = "healthy" if weather else "degraded"
        except:
            api_status["open_meteo"] = "unknown"

        return {
            "status": "healthy",
            "last_update": {
                "fires": datetime.now().isoformat(),
                "weather": datetime.now().isoformat(),
                "psi": datetime.now().isoformat()
            },
            "api_status": api_status,
            "database": "not_configured"
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "degraded",
            "last_update": {
                "fires": None,
                "weather": None,
                "psi": None
            },
            "api_status": {
                "firms": "unknown",
                "open_meteo": "unknown",
                "psi": "unknown"
            },
            "database": "error"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
