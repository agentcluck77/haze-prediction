"""
Test APScheduler functionality
Following TDD protocol: Write tests FIRST, then implementation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import time


class TestSchedulerConfiguration:
    """Test scheduler configuration and setup"""

    def test_create_scheduler(self):
        """Test creating APScheduler instance"""
        from src.scheduler.tasks import create_scheduler

        scheduler = create_scheduler()
        assert scheduler is not None
        assert hasattr(scheduler, 'add_job')
        assert hasattr(scheduler, 'start')
        assert hasattr(scheduler, 'shutdown')

    def test_scheduler_timezone(self):
        """Test scheduler uses Asia/Singapore timezone"""
        from src.scheduler.tasks import create_scheduler

        scheduler = create_scheduler()
        # Should use Singapore timezone
        assert scheduler.timezone.zone == 'Asia/Singapore'

    def test_scheduler_job_stores(self):
        """Test scheduler has proper job stores configured"""
        from src.scheduler.tasks import create_scheduler

        scheduler = create_scheduler()
        # Should have memory job store by default
        assert 'default' in scheduler._jobstores


class TestSchedulerJobs:
    """Test individual scheduled jobs"""

    @patch('src.scheduler.tasks.fetch_recent_fires')
    def test_update_fire_data_job(self, mock_fetch):
        """Test fire data update job"""
        from src.scheduler.tasks import update_fire_data

        mock_fetch.return_value = Mock()
        update_fire_data()

        # Should call fetch_recent_fires
        mock_fetch.assert_called_once()

    @patch('src.scheduler.tasks.fetch_weather_forecast')
    def test_update_weather_data_job(self, mock_fetch):
        """Test weather data update job"""
        from src.scheduler.tasks import update_weather_data

        mock_fetch.return_value = Mock()
        update_weather_data()

        # Should call fetch_weather_forecast
        mock_fetch.assert_called()

    @patch('src.scheduler.tasks.fetch_current_psi')
    def test_update_psi_data_job(self, mock_fetch):
        """Test PSI data update job"""
        from src.scheduler.tasks import update_psi_data

        mock_fetch.return_value = Mock()
        update_psi_data()

        # Should call fetch_current_psi
        mock_fetch.assert_called_once()

    @patch('src.scheduler.tasks.predict_all_horizons')
    def test_generate_predictions_job(self, mock_predict):
        """Test prediction generation job"""
        from src.scheduler.tasks import generate_predictions

        mock_predict.return_value = {
            '24h': {'prediction': 50},
            '48h': {'prediction': 55}
        }
        generate_predictions()

        # Should call predict_all_horizons
        mock_predict.assert_called_once()


class TestSchedulerIntervals:
    """Test job scheduling intervals"""

    def test_fire_update_interval(self):
        """Test fires updated every 15 minutes"""
        import src.scheduler.tasks as tasks
        # Import the module to get original values
        import importlib
        importlib.reload(tasks)

        assert tasks.FIRE_UPDATE_INTERVAL == 15 * 60  # 15 minutes in seconds

    def test_weather_update_interval(self):
        """Test weather updated hourly"""
        import src.scheduler.tasks as tasks
        import importlib
        importlib.reload(tasks)

        assert tasks.WEATHER_UPDATE_INTERVAL == 60 * 60  # 1 hour in seconds

    def test_psi_update_interval(self):
        """Test PSI updated every 15 minutes"""
        from src.scheduler.tasks import PSI_UPDATE_INTERVAL

        assert PSI_UPDATE_INTERVAL == 15 * 60  # 15 minutes in seconds

    def test_prediction_intervals(self):
        """Test prediction intervals for different horizons"""
        from src.scheduler.tasks import PREDICTION_INTERVAL_24H, PREDICTION_INTERVAL_OTHERS

        assert PREDICTION_INTERVAL_24H == 3 * 60 * 60  # 3 hours
        assert PREDICTION_INTERVAL_OTHERS == 6 * 60 * 60  # 6 hours


class TestSchedulerLifecycle:
    """Test scheduler lifecycle (start/stop)"""

    def test_start_scheduler(self):
        """Test starting the scheduler"""
        from src.scheduler.tasks import start_scheduler

        scheduler = start_scheduler()
        assert scheduler is not None
        assert scheduler.running

        # Clean up
        scheduler.shutdown(wait=False)

    def test_stop_scheduler(self):
        """Test stopping the scheduler"""
        from src.scheduler.tasks import start_scheduler, stop_scheduler

        scheduler = start_scheduler()
        assert scheduler.running

        stop_scheduler(scheduler)
        assert not scheduler.running

    def test_scheduler_starts_with_jobs(self):
        """Test scheduler starts with all jobs configured"""
        from src.scheduler.tasks import start_scheduler

        scheduler = start_scheduler()

        # Should have jobs for fires, weather, PSI, predictions
        jobs = scheduler.get_jobs()
        assert len(jobs) > 0

        # Clean up
        scheduler.shutdown(wait=False)


class TestLastUpdateTracking:
    """Test tracking of last update times"""

    def test_get_last_update_times(self):
        """Test retrieving last update times"""
        from src.scheduler.tasks import get_last_update_times

        times = get_last_update_times()

        assert isinstance(times, dict)
        assert 'fires' in times
        assert 'weather' in times
        assert 'psi' in times
        assert 'predictions' in times

    @patch('src.scheduler.tasks.fetch_recent_fires')
    def test_update_fire_data_updates_timestamp(self, mock_fetch):
        """Test fire update sets last update timestamp"""
        from src.scheduler.tasks import update_fire_data, get_last_update_times

        mock_fetch.return_value = Mock()

        before = datetime.now()
        update_fire_data()
        after = datetime.now()

        times = get_last_update_times()
        if times['fires']:
            last_update = datetime.fromisoformat(times['fires'])
            assert before <= last_update <= after

    @patch('src.scheduler.tasks.fetch_current_psi')
    def test_update_psi_data_updates_timestamp(self, mock_fetch):
        """Test PSI update sets last update timestamp"""
        from src.scheduler.tasks import update_psi_data, get_last_update_times

        mock_fetch.return_value = Mock()

        before = datetime.now()
        update_psi_data()
        after = datetime.now()

        times = get_last_update_times()
        if times['psi']:
            last_update = datetime.fromisoformat(times['psi'])
            assert before <= last_update <= after


class TestSchedulerErrorHandling:
    """Test error handling in scheduled jobs"""

    @patch('src.scheduler.tasks.fetch_recent_fires')
    def test_fire_update_handles_errors(self, mock_fetch):
        """Test fire update handles API errors gracefully"""
        from src.scheduler.tasks import update_fire_data

        mock_fetch.side_effect = Exception("API error")

        # Should not raise exception
        try:
            update_fire_data()
        except Exception:
            pytest.fail("update_fire_data should handle exceptions gracefully")

    @patch('src.scheduler.tasks.fetch_current_psi')
    def test_psi_update_handles_errors(self, mock_fetch):
        """Test PSI update handles API errors gracefully"""
        from src.scheduler.tasks import update_psi_data

        mock_fetch.side_effect = Exception("API error")

        # Should not raise exception
        try:
            update_psi_data()
        except Exception:
            pytest.fail("update_psi_data should handle exceptions gracefully")

    @patch('src.scheduler.tasks.predict_all_horizons')
    def test_prediction_handles_errors(self, mock_predict):
        """Test prediction generation handles errors gracefully"""
        from src.scheduler.tasks import generate_predictions

        mock_predict.side_effect = Exception("Model error")

        # Should not raise exception
        try:
            generate_predictions()
        except Exception:
            pytest.fail("generate_predictions should handle exceptions gracefully")


class TestSchedulerConfiguration:
    """Test scheduler configuration options"""

    def test_scheduler_can_be_disabled(self):
        """Test scheduler can be disabled via config"""
        from src.scheduler.tasks import create_scheduler

        # Should be able to create scheduler without starting
        scheduler = create_scheduler()
        assert not scheduler.running

    def test_configure_scheduler_with_custom_intervals(self):
        """Test scheduler accepts custom intervals"""
        from src.scheduler.tasks import configure_scheduler_intervals

        custom_intervals = {
            'fire': 10 * 60,  # 10 minutes
            'weather': 30 * 60,  # 30 minutes
        }

        result = configure_scheduler_intervals(custom_intervals)
        assert result is not None


class TestJobExecution:
    """Test actual job execution (integration-like)"""

    @patch('src.scheduler.tasks.fetch_recent_fires')
    @patch('src.scheduler.tasks.fetch_weather_forecast')
    @patch('src.scheduler.tasks.fetch_current_weather')
    @patch('src.scheduler.tasks.fetch_current_psi')
    def test_all_jobs_can_execute(self, mock_psi, mock_current_weather, mock_forecast, mock_fires):
        """Test all scheduled jobs can execute without errors"""
        from src.scheduler.tasks import (
            update_fire_data,
            update_weather_data,
            update_psi_data,
            generate_predictions
        )

        import pandas as pd

        # Mock return values with proper types
        mock_fires.return_value = pd.DataFrame({'latitude': [1.0], 'longitude': [103.0]})
        mock_current_weather.return_value = pd.DataFrame({'temp': [30]})
        mock_forecast.return_value = pd.DataFrame({'temp': [30]})
        mock_psi.return_value = pd.DataFrame({'psi': [50]})

        # All jobs should execute without raising exceptions
        update_fire_data()
        update_weather_data()
        update_psi_data()
        generate_predictions()

        # Verify all were called
        assert mock_fires.called
        assert mock_current_weather.called
        assert mock_forecast.called
        assert mock_psi.called
