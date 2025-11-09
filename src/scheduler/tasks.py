"""
APScheduler tasks for periodic data updates
Handles scheduled jobs for fires, weather, PSI, and predictions
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import pytz
import logging

from src.data_ingestion.firms import fetch_recent_fires
from src.data_ingestion.weather import fetch_weather_forecast, fetch_current_weather
from src.data_ingestion.psi import fetch_current_psi
from src.api.prediction import predict_all_horizons


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Update intervals (in seconds)
FIRE_UPDATE_INTERVAL = 15 * 60  # 15 minutes
WEATHER_UPDATE_INTERVAL = 60 * 60  # 1 hour
PSI_UPDATE_INTERVAL = 15 * 60  # 15 minutes
PREDICTION_INTERVAL_24H = 3 * 60 * 60  # 3 hours for 24h predictions
PREDICTION_INTERVAL_OTHERS = 6 * 60 * 60  # 6 hours for 48h, 72h, 7d


# Global tracking of last update times
_last_update_times = {
    'fires': None,
    'weather': None,
    'psi': None,
    'predictions': None
}


# Global scheduler instance
_scheduler_instance = None


def create_scheduler():
    """
    Create APScheduler instance configured for Singapore timezone

    Returns:
        BackgroundScheduler: Configured scheduler
    """
    singapore_tz = pytz.timezone('Asia/Singapore')

    scheduler = BackgroundScheduler(
        timezone=singapore_tz,
        job_defaults={
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1  # Only one instance of each job at a time
        }
    )

    return scheduler


def update_fire_data():
    """
    Scheduled job to fetch latest fire detection data

    Updates every 15 minutes
    """
    try:
        logger.info("Updating fire data...")
        fires = fetch_recent_fires(days=1)
        _last_update_times['fires'] = datetime.now().isoformat()
        logger.info(f"Fire data updated successfully: {len(fires)} fires detected")
    except Exception as e:
        logger.error(f"Failed to update fire data: {str(e)}")


def update_weather_data():
    """
    Scheduled job to fetch latest weather forecast

    Updates hourly
    """
    try:
        logger.info("Updating weather data...")
        # Fetch current weather for Singapore
        weather = fetch_current_weather(latitude=1.3521, longitude=103.8198)
        # Also fetch forecast
        forecast = fetch_weather_forecast(lat=1.3521, lon=103.8198, hours=168)
        _last_update_times['weather'] = datetime.now().isoformat()
        logger.info("Weather data updated successfully")
    except Exception as e:
        logger.error(f"Failed to update weather data: {str(e)}")


def update_psi_data():
    """
    Scheduled job to fetch latest PSI readings

    Updates every 15 minutes
    """
    try:
        logger.info("Updating PSI data...")
        psi_data = fetch_current_psi()
        _last_update_times['psi'] = datetime.now().isoformat()
        logger.info("PSI data updated successfully")
    except Exception as e:
        logger.error(f"Failed to update PSI data: {str(e)}")


def generate_predictions():
    """
    Scheduled job to generate PSI predictions for all horizons

    24h predictions: Every 3 hours
    48h, 72h, 7d predictions: Every 6 hours
    """
    try:
        logger.info("Generating predictions for all horizons...")
        predictions = predict_all_horizons()
        _last_update_times['predictions'] = datetime.now().isoformat()
        logger.info(f"Predictions generated successfully for {len(predictions)} horizons")

        # Log prediction values for monitoring
        for horizon, pred in predictions.items():
            logger.info(f"  {horizon}: {pred.get('prediction', 'N/A')} PSI")

    except Exception as e:
        logger.error(f"Failed to generate predictions: {str(e)}")


def get_last_update_times():
    """
    Get last update times for all data sources

    Returns:
        dict: Dictionary with last update timestamps
    """
    return _last_update_times.copy()


def configure_scheduler_intervals(custom_intervals):
    """
    Configure custom update intervals

    Args:
        custom_intervals: Dict with custom interval values

    Returns:
        dict: Updated intervals
    """
    global FIRE_UPDATE_INTERVAL, WEATHER_UPDATE_INTERVAL

    if 'fire' in custom_intervals:
        FIRE_UPDATE_INTERVAL = custom_intervals['fire']

    if 'weather' in custom_intervals:
        WEATHER_UPDATE_INTERVAL = custom_intervals['weather']

    return {
        'fire': FIRE_UPDATE_INTERVAL,
        'weather': WEATHER_UPDATE_INTERVAL,
        'psi': PSI_UPDATE_INTERVAL,
        'prediction_24h': PREDICTION_INTERVAL_24H,
        'prediction_others': PREDICTION_INTERVAL_OTHERS
    }


def start_scheduler():
    """
    Start the scheduler with all configured jobs

    Returns:
        BackgroundScheduler: Running scheduler instance
    """
    global _scheduler_instance

    scheduler = create_scheduler()

    # Add jobs for each data source
    scheduler.add_job(
        update_fire_data,
        trigger=IntervalTrigger(seconds=FIRE_UPDATE_INTERVAL),
        id='update_fires',
        name='Update Fire Data',
        replace_existing=True
    )

    scheduler.add_job(
        update_weather_data,
        trigger=IntervalTrigger(seconds=WEATHER_UPDATE_INTERVAL),
        id='update_weather',
        name='Update Weather Data',
        replace_existing=True
    )

    scheduler.add_job(
        update_psi_data,
        trigger=IntervalTrigger(seconds=PSI_UPDATE_INTERVAL),
        id='update_psi',
        name='Update PSI Data',
        replace_existing=True
    )

    scheduler.add_job(
        generate_predictions,
        trigger=IntervalTrigger(seconds=PREDICTION_INTERVAL_24H),
        id='generate_predictions',
        name='Generate Predictions',
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    _scheduler_instance = scheduler

    logger.info("Scheduler started successfully")
    logger.info(f"  - Fire updates: every {FIRE_UPDATE_INTERVAL // 60} minutes")
    logger.info(f"  - Weather updates: every {WEATHER_UPDATE_INTERVAL // 60} minutes")
    logger.info(f"  - PSI updates: every {PSI_UPDATE_INTERVAL // 60} minutes")
    logger.info(f"  - Predictions: every {PREDICTION_INTERVAL_24H // 60 // 60} hours")

    return scheduler


def stop_scheduler(scheduler=None):
    """
    Stop the scheduler gracefully

    Args:
        scheduler: Scheduler instance to stop (uses global if None)
    """
    global _scheduler_instance

    if scheduler is None:
        scheduler = _scheduler_instance

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")

    _scheduler_instance = None


def get_scheduler_status():
    """
    Get current scheduler status

    Returns:
        dict: Status information including running state and jobs
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        return {
            'running': False,
            'jobs': [],
            'last_updates': get_last_update_times()
        }

    jobs = []
    for job in _scheduler_instance.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })

    return {
        'running': _scheduler_instance.running,
        'jobs': jobs,
        'last_updates': get_last_update_times()
    }


if __name__ == "__main__":
    # Start scheduler when run directly
    try:
        scheduler = start_scheduler()

        # Keep running
        import time
        logger.info("Scheduler is running. Press Ctrl+C to stop.")

        while True:
            time.sleep(60)
            # Print status every minute
            status = get_scheduler_status()
            logger.info(f"Status: {len(status['jobs'])} jobs active")

    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        stop_scheduler()
